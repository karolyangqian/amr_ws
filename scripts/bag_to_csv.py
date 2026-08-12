import csv
import sys
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message
import rosbag2_py

def convert_bag_to_csv(bag_path, csv_output_path):
    # Set up ROS2 bag reader
    reader = rosbag2_py.SequentialReader()
    
    # Configure storage options (works for both sqlite3 and mcap formats)
    storage_options = rosbag2_py.StorageOptions(uri=bag_path, storage_id="")
    converter_options = rosbag2_py.ConverterOptions(
        input_serialization_format="cdr",
        output_serialization_format="cdr"
    )
    reader.open(storage_options, converter_options)

    # Get metadata to map topic names to their data types
    topic_types = reader.get_all_topics_and_types()
    type_map = {topic.name: topic.type for topic in topic_types}

    # Filter to only parse your specified topics
    target_topics = ["/cmd_vel", "/motor_feedback"]
    storage_filter = rosbag2_py.StorageFilter(topics=target_topics)
    reader.set_filter(storage_filter)

    # Open CSV file for writing
    with open(csv_output_path, mode='w', newline='') as csv_file:
        # Define flat columns for the CSV
        fieldnames = [
            "timestamp_ns", "topic",
            "cmd_vel_linear_x", "cmd_vel_angular_z",
            "motor_feedback_position", "motor_feedback_velocity"
        ]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        print(f"Reading from bag: {bag_path}...")
        
        while reader.has_next():
            # Read next serialized message from the queue
            (topic, data, timestamp) = reader.read_next()
            
            # Dynamically look up the message type and deserialize it
            msg_type_str = type_map[topic]
            msg_type = get_message(msg_type_str)
            msg = deserialize_message(data, msg_type)

            # Initialize a blank row dictionary for this timestamp entry
            row = {
                "timestamp_ns": timestamp,
                "topic": topic,
                "cmd_vel_linear_x": "",
                "cmd_vel_angular_z": "",
                "motor_feedback_position": "",
                "motor_feedback_velocity": ""
            }

            # Map fields safely depending on which topic the message came from
            if topic == "/cmd_vel":
                # Assuming standard geometry_msgs/msg/Twist
                row["cmd_vel_linear_x"] = msg.linear.x
                row["cmd_vel_angular_z"] = msg.angular.z
            elif topic == "/motor_feedback":
                # Adjust these attributes according to your custom motor message type
                row["motor_feedback_position"] = getattr(msg, 'position', '')
                row["motor_feedback_velocity"] = getattr(msg, 'velocity', '')

            writer.writerow(row)

    print(f"Successfully exported data to {csv_output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 scripts/bag_to_csv.py scripts pid.csv")
        sys.exit(1)
        
    convert_bag_to_csv(sys.argv[1], sys.argv[2])
