#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/laser_scan.hpp>
#include <geometry_msgs/msg/transform_stamped.hpp>
#include <tf2_ros/buffer.h>
#include <tf2_ros/transform_listener.h>
#include <tf2_geometry_msgs/tf2_geometry_msgs.hpp>
#include <tf2/LinearMath/Transform.h>

#include <cmath>
#include <vector>
#include <string>
#include <map>
#include <memory>
#include <limits>
#include <algorithm>
#include <chrono>

class SimpleScanMerger : public rclcpp::Node
{
public:
  SimpleScanMerger() : Node("simple_scan_merger")
  {
    // Declare parameters with default values
    this->declare_parameter<std::string>("target_frame", "base_link");
    this->declare_parameter<std::string>("merged_topic", "/scan");
    this->declare_parameter<std::vector<std::string>>("scan_topics", {"/front_scan", "/rear_scan"});

    this->declare_parameter<double>("angle_min", -M_PI);
    this->declare_parameter<double>("angle_max", M_PI);
    this->declare_parameter<double>("angle_increment", 0.00872664625); // ~0.5 degree
    this->declare_parameter<double>("scan_time", 0.1);
    this->declare_parameter<double>("range_min", 0.03);
    this->declare_parameter<double>("range_max", 12.0);
    this->declare_parameter<double>("min_height", -0.5);
    this->declare_parameter<double>("max_height", 1.0);
    this->declare_parameter<bool>("use_tf", true);
    this->declare_parameter<double>("transform_tolerance", 0.2);
    this->declare_parameter<std::string>("qos_reliability", "reliable");
    this->declare_parameter<double>("publish_rate", 10.0);
    this->declare_parameter<double>("scan_timeout", 0.5);

    // Load parameters
    target_frame_ = this->get_parameter("target_frame").as_string();
    merged_topic_ = this->get_parameter("merged_topic").as_string();
    scan_topics_ = this->get_parameter("scan_topics").as_string_array();

    angle_min_ = this->get_parameter("angle_min").as_double();
    angle_max_ = this->get_parameter("angle_max").as_double();
    angle_increment_ = this->get_parameter("angle_increment").as_double();
    scan_time_ = this->get_parameter("scan_time").as_double();
    range_min_ = this->get_parameter("range_min").as_double();
    range_max_ = this->get_parameter("range_max").as_double();
    min_height_ = this->get_parameter("min_height").as_double();
    max_height_ = this->get_parameter("max_height").as_double();
    use_tf_ = this->get_parameter("use_tf").as_bool();
    transform_tolerance_ = this->get_parameter("transform_tolerance").as_double();
    qos_reliability_ = this->get_parameter("qos_reliability").as_string();
    publish_rate_ = this->get_parameter("publish_rate").as_double();
    scan_timeout_ = this->get_parameter("scan_timeout").as_double();

    // TF Setup
    if (use_tf_) {
      tf_buffer_ = std::make_shared<tf2_ros::Buffer>(this->get_clock());
      tf_listener_ = std::make_shared<tf2_ros::TransformListener>(*tf_buffer_);
    }

    // QoS Setup for Publisher
    auto pub_qos = rclcpp::QoS(rclcpp::KeepLast(10));
    if (qos_reliability_ == "reliable") {
      pub_qos.reliable();
    } else {
      pub_qos.best_effort();
    }
    merged_pub_ = this->create_publisher<sensor_msgs::msg::LaserScan>(merged_topic_, pub_qos);

    // Subscriptions setup with SensorDataQoS (Best Effort compatible)
    auto sub_qos = rclcpp::SensorDataQoS();
    for (const auto & topic : scan_topics_) {
      RCLCPP_INFO(this->get_logger(), "Subscribing to scan topic: %s", topic.c_str());
      subscribers_.push_back(
        this->create_subscription<sensor_msgs::msg::LaserScan>(
          topic, sub_qos,
          [this, topic](const sensor_msgs::msg::LaserScan::SharedPtr msg) {
            this->scan_callback(topic, msg);
          }
        )
      );
    }

    // Timer Setup for constant publish rate
    if (publish_rate_ > 0.0) {
      auto period = std::chrono::duration<double>(1.0 / publish_rate_);
      timer_ = this->create_wall_timer(
        period, std::bind(&SimpleScanMerger::timer_callback, this));
    } else {
      RCLCPP_ERROR(this->get_logger(), "publish_rate must be > 0.0");
    }

    RCLCPP_INFO(
      this->get_logger(),
      "SimpleScanMerger initialized. Merging [%zu] topics into [%s] at %.1f Hz (target_frame: %s, timeout: %.2fs, qos: %s)",
      scan_topics_.size(), merged_topic_.c_str(), publish_rate_, target_frame_.c_str(), scan_timeout_, qos_reliability_.c_str()
    );
  }

private:
  void scan_callback(const std::string & topic, const sensor_msgs::msg::LaserScan::SharedPtr msg)
  {
    scans_[topic] = msg;
    last_receive_times_[topic] = this->now();
  }

  void timer_callback()
  {
    merge_and_publish();
  }

  void merge_and_publish()
  {
    if (scan_topics_.empty()) {
      return;
    }

    if (angle_increment_ <= 0.0 || angle_max_ <= angle_min_) {
      RCLCPP_ERROR_THROTTLE(this->get_logger(), *this->get_clock(), 5000, "Invalid angle parameters!");
      return;
    }

    rclcpp::Time current_time = this->now();
    size_t num_topics = scan_topics_.size();
    std::vector<bool> is_alive(num_topics, false);

    // 1. Evaluate ALIVE status for each scan topic
    for (size_t i = 0; i < num_topics; ++i) {
      const std::string & topic = scan_topics_[i];
      if (scans_.count(topic) > 0 && scans_[topic] && last_receive_times_.count(topic) > 0) {
        double elapsed = (current_time - last_receive_times_[topic]).seconds();
        if (elapsed >= 0.0 && elapsed <= scan_timeout_) {
          is_alive[i] = true;
        }
      }
    }

    // 2. Sticky Master Clock Selection Logic with Cyclic Failover
    bool current_master_valid = (current_master_idx_ >= 0 &&
                                 static_cast<size_t>(current_master_idx_) < num_topics &&
                                 is_alive[current_master_idx_]);

    if (!current_master_valid) {
      int new_master = -1;
      int start_idx = (current_master_idx_ >= 0) ? (current_master_idx_ + 1) % static_cast<int>(num_topics) : 0;
      for (size_t step = 0; step < num_topics; ++step) {
        int candidate = (start_idx + static_cast<int>(step)) % static_cast<int>(num_topics);
        if (is_alive[candidate]) {
          new_master = candidate;
          break;
        }
      }

      if (new_master != -1) {
        current_master_idx_ = new_master;
        RCLCPP_INFO(
          this->get_logger(),
          "Master clock assigned to topic [%zu]: %s",
          static_cast<size_t>(current_master_idx_), scan_topics_[current_master_idx_].c_str()
        );
      } else {
        current_master_idx_ = -1;
        RCLCPP_WARN_THROTTLE(
          this->get_logger(), *this->get_clock(), 5000,
          "All lidar scan topics inactive. Skipping merged scan publish."
        );
        return; // STOP publishing when ALL lidars are dead!
      }
    }

    // 3. Determine Master Timestamp
    const std::string & master_topic = scan_topics_[current_master_idx_];
    rclcpp::Time master_stamp(scans_[master_topic]->header.stamp);

    // Enforce strictly monotonic timestamps for slam_toolbox
    if (last_published_stamp_.nanoseconds() > 0 && master_stamp <= last_published_stamp_) {
      master_stamp = last_published_stamp_ + rclcpp::Duration(0, 100000); // add 100 microseconds
    }

    // 4. Construct Merged LaserScan
    size_t num_bins = static_cast<size_t>(std::round((angle_max_ - angle_min_) / angle_increment_));
    if (num_bins == 0) num_bins = 1;
    sensor_msgs::msg::LaserScan merged_scan;

    merged_scan.header.stamp = master_stamp;
    merged_scan.header.frame_id = target_frame_;
    merged_scan.angle_min = static_cast<float>(angle_min_);
    merged_scan.angle_max = static_cast<float>(angle_min_ + (num_bins - 1) * angle_increment_);
    merged_scan.angle_increment = static_cast<float>(angle_increment_);
    merged_scan.time_increment = static_cast<float>(angle_increment_ / (2.0 * M_PI / scan_time_));
    merged_scan.scan_time = static_cast<float>(scan_time_);
    merged_scan.range_min = static_cast<float>(range_min_);
    merged_scan.range_max = static_cast<float>(range_max_);

    merged_scan.ranges.assign(num_bins, std::numeric_limits<float>::infinity());
    merged_scan.intensities.assign(num_bins, 0.0f);
    bool has_any_intensity = false;

    // 5. Merge points from ALL ALIVE topics
    for (size_t i = 0; i < num_topics; ++i) {
      if (!is_alive[i]) continue;

      const std::string & topic = scan_topics_[i];
      const auto & scan_msg = scans_[topic];
      if (!scan_msg) continue;

      tf2::Transform tf2_transform;
      tf2_transform.setIdentity();

      if (use_tf_ && tf_buffer_) {
        try {
          geometry_msgs::msg::TransformStamped transform_stamped =
            tf_buffer_->lookupTransform(
              target_frame_, scan_msg->header.frame_id,
              tf2::TimePointZero,
              tf2::durationFromSec(transform_tolerance_)
            );
          tf2::fromMsg(transform_stamped.transform, tf2_transform);
        } catch (const tf2::TransformException & ex) {
          RCLCPP_WARN_THROTTLE(
            this->get_logger(), *this->get_clock(), 2000,
            "Could not transform %s to %s: %s",
            scan_msg->header.frame_id.c_str(), target_frame_.c_str(), ex.what()
          );
          continue;
        }
      }

      bool scan_has_intensities = (scan_msg->intensities.size() == scan_msg->ranges.size());

      for (size_t j = 0; j < scan_msg->ranges.size(); ++j) {
        float r = scan_msg->ranges[j];
        if (!std::isfinite(r) || r < scan_msg->range_min || r > scan_msg->range_max) {
          continue;
        }

        double angle = scan_msg->angle_min + j * scan_msg->angle_increment;
        double x_sensor = r * std::cos(angle);
        double y_sensor = r * std::sin(angle);
        double z_sensor = 0.0;

        tf2::Vector3 pt_in(x_sensor, y_sensor, z_sensor);
        tf2::Vector3 pt_out = tf2_transform * pt_in;

        double x_tgt = pt_out.x();
        double y_tgt = pt_out.y();
        double z_tgt = pt_out.z();

        if (z_tgt < min_height_ || z_tgt > max_height_) {
          continue;
        }

        double r_tgt = std::hypot(x_tgt, y_tgt);
        double theta_tgt = std::atan2(y_tgt, x_tgt);

        if (r_tgt < range_min_ || r_tgt > range_max_) {
          continue;
        }

        if (theta_tgt < angle_min_ || theta_tgt > angle_max_) {
          continue;
        }

        int index = static_cast<int>(std::round((theta_tgt - angle_min_) / angle_increment_));
        if (index >= 0 && static_cast<size_t>(index) < num_bins) {
          if (r_tgt < merged_scan.ranges[index]) {
            merged_scan.ranges[index] = static_cast<float>(r_tgt);
            if (scan_has_intensities) {
              merged_scan.intensities[index] = scan_msg->intensities[j];
              has_any_intensity = true;
            }
          }
        }
      }
    }

    if (!has_any_intensity) {
      merged_scan.intensities.clear();
    }

    merged_pub_->publish(merged_scan);
    last_published_stamp_ = master_stamp;
  }

  // Parameters
  std::string target_frame_;
  std::string merged_topic_;
  std::vector<std::string> scan_topics_;
  double angle_min_;
  double angle_max_;
  double angle_increment_;
  double scan_time_;
  double range_min_;
  double range_max_;
  double min_height_;
  double max_height_;
  bool use_tf_;
  double transform_tolerance_;
  std::string qos_reliability_;
  double publish_rate_;
  double scan_timeout_;

  // State
  int current_master_idx_{-1};
  rclcpp::Time last_published_stamp_{0, 0, RCL_ROS_TIME};
  std::map<std::string, rclcpp::Time> last_receive_times_;

  // ROS handles
  std::shared_ptr<tf2_ros::Buffer> tf_buffer_;
  std::shared_ptr<tf2_ros::TransformListener> tf_listener_;
  rclcpp::Publisher<sensor_msgs::msg::LaserScan>::SharedPtr merged_pub_;
  std::vector<rclcpp::Subscription<sensor_msgs::msg::LaserScan>::SharedPtr> subscribers_;
  rclcpp::TimerBase::SharedPtr timer_;

  // Cache
  std::map<std::string, sensor_msgs::msg::LaserScan::SharedPtr> scans_;
};

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<SimpleScanMerger>());
  rclcpp::shutdown();
  return 0;
}
