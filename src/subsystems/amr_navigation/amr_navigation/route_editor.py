#!/usr/bin/env python3

import json
import os
import threading

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import PointStamped
from visualization_msgs.msg import Marker, MarkerArray


class RouteEditor(Node):

    def __init__(self):
        super().__init__('route_editor')

        self.nodes = []
        self.edges = []

        self.output_file = os.path.expanduser(
            '~/Documents/rein_amr/amr_ws/src/subsystems/'
            'amr_navigation/config/route_graph.geojson'
        )

        # Node yang baru saja dibuat dan menunggu konfirmasi
        self.pending_node_id = None

        # ----------------------------------------------------------
        # SUBSCRIBE CLICKED POINT
        # ----------------------------------------------------------

        self.clicked_sub = self.create_subscription(
            PointStamped,
            '/clicked_point',
            self.clicked_point_callback,
            10
        )

        # ----------------------------------------------------------
        # MARKER PUBLISHER
        # ----------------------------------------------------------

        self.marker_pub = self.create_publisher(
            MarkerArray,
            '/route_editor/markers',
            10
        )

        # ----------------------------------------------------------
        # INFO
        # ----------------------------------------------------------

        self.get_logger().info('======================================')
        self.get_logger().info('        NAV2 ROUTE EDITOR')
        self.get_logger().info('======================================')
        self.get_logger().info('Klik map di RViz -> tambah node')
        self.get_logger().info('')
        self.get_logger().info('Setelah klik node:')
        self.get_logger().info('  k = gunakan posisi hasil klik')
        self.get_logger().info('  r = rapikan posisi secara manual')
        self.get_logger().info('')
        self.get_logger().info('Command:')
        self.get_logger().info('  s = save GeoJSON')
        self.get_logger().info('  e = buat edge')
        self.get_logger().info('  l = lihat node dan edge')
        self.get_logger().info('  r = reset semua')
        self.get_logger().info('  q = quit')
        self.get_logger().info('======================================')

        # Keyboard thread
        self.keyboard_thread = threading.Thread(
            target=self.keyboard_loop,
            daemon=True
        )
        self.keyboard_thread.start()

    # ==========================================================
    # CLICK RVIZ
    # ==========================================================

    def clicked_point_callback(self, msg):

        x = msg.point.x
        y = msg.point.y

        node_id = len(self.nodes)

        node = {
            'id': node_id,
            'x': x,
            'y': y
        }

        self.nodes.append(node)

        self.pending_node_id = node_id

        self.get_logger().info('')
        self.get_logger().info('--------------------------------------')
        self.get_logger().info(
            f'Node {node_id} dibuat: '
            f'x={x:.4f}, y={y:.4f}'
        )
        self.get_logger().info(
            'Gunakan [k] untuk mempertahankan posisi '
            'atau [r] untuk merapikan manual.'
        )
        self.get_logger().info('--------------------------------------')

        self.publish_markers()

    # ==========================================================
    # MANUAL NODE POSITION
    # ==========================================================

    def manual_edit_node(self):

        if self.pending_node_id is None:
            self.get_logger().warn(
                'Tidak ada node yang menunggu konfirmasi.'
            )
            return

        node_id = self.pending_node_id
        node = self.nodes[node_id]

        try:
            print('')
            print(f'Node {node_id} sekarang:')
            print(f'  X = {node["x"]}')
            print(f'  Y = {node["y"]}')

            new_x = float(input('Masukkan X baru: '))
            new_y = float(input('Masukkan Y baru: '))

            node['x'] = new_x
            node['y'] = new_y

            self.get_logger().info(
                f'Node {node_id} diperbarui: '
                f'x={new_x:.4f}, y={new_y:.4f}'
            )

            self.pending_node_id = None
            self.publish_markers()

        except ValueError:
            self.get_logger().error(
                'Input tidak valid. Gunakan angka.'
            )

    # ==========================================================
    # KEEP NODE
    # ==========================================================

    def keep_node(self):

        if self.pending_node_id is None:
            self.get_logger().warn(
                'Tidak ada node yang menunggu konfirmasi.'
            )
            return

        node_id = self.pending_node_id

        self.get_logger().info(
            f'Node {node_id} dipertahankan.'
        )

        self.pending_node_id = None

    # ==========================================================
    # CREATE EDGE
    # ==========================================================

    def create_edge_interactive(self):

        if len(self.nodes) < 2:
            self.get_logger().warn(
                'Minimal harus ada 2 node.'
            )
            return

        # Jangan membuat edge ketika masih ada node
        # yang belum dikonfirmasi
        if self.pending_node_id is not None:
            self.get_logger().warn(
                f'Node {self.pending_node_id} belum dikonfirmasi. '
                'Gunakan k atau r terlebih dahulu.'
            )
            return

        print('')
        print('======================================')
        print('          CREATE EDGE')
        print('======================================')

        self.print_nodes()

        try:
            start_id = int(input('Start node ID: '))

            if not self.node_exists(start_id):
                print(f'Node {start_id} tidak ada.')
                return

            destination_input = input(
                'Destination node ID '
                '(contoh: 1 atau 1,2,3): '
            )

            destination_ids = [
                int(x.strip())
                for x in destination_input.split(',')
                if x.strip()
            ]

            # Validasi semua destination
            for dest_id in destination_ids:
                if not self.node_exists(dest_id):
                    print(f'Node {dest_id} tidak ada.')
                    return

                if dest_id == start_id:
                    print(
                        'Start dan destination tidak boleh sama.'
                    )
                    return

            bidirectional = input(
                'Bidirectional? [y/n]: '
            ).strip().lower()

            for dest_id in destination_ids:

                # Forward edge
                self.add_edge(
                    start_id,
                    dest_id
                )

                # Reverse edge
                if bidirectional == 'y':
                    self.add_edge(
                        dest_id,
                        start_id
                    )

            self.publish_markers()

            print('')
            print('Edge berhasil dibuat.')
            self.print_edges()
            print('======================================')

        except ValueError:
            print('Input harus berupa angka.')

    # ==========================================================
    # ADD EDGE
    # ==========================================================

    def add_edge(self, start_id, end_id):

        # Cek apakah edge sudah ada
        for edge in self.edges:

            if (
                edge['startid'] == start_id
                and edge['endid'] == end_id
            ):
                self.get_logger().warn(
                    f'Edge {start_id} -> {end_id} '
                    'sudah ada.'
                )
                return

        edge = {
            'id': len(self.edges),
            'startid': start_id,
            'endid': end_id
        }

        self.edges.append(edge)

        self.get_logger().info(
            f'Edge {start_id} -> {end_id} dibuat.'
        )

    # ==========================================================
    # NODE EXISTS
    # ==========================================================

    def node_exists(self, node_id):

        return any(
            node['id'] == node_id
            for node in self.nodes
        )

    # ==========================================================
    # PRINT NODES
    # ==========================================================

    def print_nodes(self):

        print('')
        print('NODES:')

        if not self.nodes:
            print('  Tidak ada node.')
            return

        for node in self.nodes:

            print(
                f'  Node {node["id"]}: '
                f'x={node["x"]:.4f}, '
                f'y={node["y"]:.4f}'
            )

    # ==========================================================
    # PRINT EDGES
    # ==========================================================

    def print_edges(self):

        print('')
        print('EDGES:')

        if not self.edges:
            print('  Tidak ada edge.')
            return

        for edge in self.edges:

            print(
                f'  Edge {edge["id"]}: '
                f'{edge["startid"]} -> '
                f'{edge["endid"]}'
            )

    # ==========================================================
    # SHOW GRAPH
    # ==========================================================

    def show_graph(self):

        print('')
        print('======================================')
        print('             GRAPH')
        print('======================================')

        self.print_nodes()
        self.print_edges()

        print('======================================')

    # ==========================================================
    # RVIZ MARKERS
    # ==========================================================

    def publish_markers(self):

        marker_array = MarkerArray()

        # DELETE ALL
        delete_marker = Marker()

        delete_marker.header.frame_id = 'map'
        delete_marker.header.stamp = self.get_clock().now().to_msg()

        delete_marker.ns = 'route_editor'
        delete_marker.id = 9999
        delete_marker.action = Marker.DELETEALL

        marker_array.markers.append(delete_marker)

        # ------------------------------------------------------
        # NODES
        # ------------------------------------------------------

        for node in self.nodes:

            marker = Marker()

            marker.header.frame_id = 'map'
            marker.header.stamp = self.get_clock().now().to_msg()

            marker.ns = 'nodes'
            marker.id = node['id']

            marker.type = Marker.SPHERE
            marker.action = Marker.ADD

            marker.pose.position.x = node['x']
            marker.pose.position.y = node['y']
            marker.pose.position.z = 0.05

            marker.pose.orientation.w = 1.0

            marker.scale.x = 0.25
            marker.scale.y = 0.25
            marker.scale.z = 0.25

            marker.color.r = 0.0
            marker.color.g = 1.0
            marker.color.b = 0.0
            marker.color.a = 1.0

            marker_array.markers.append(marker)

            # NODE TEXT

            text = Marker()

            text.header.frame_id = 'map'
            text.header.stamp = self.get_clock().now().to_msg()

            text.ns = 'node_labels'
            text.id = 1000 + node['id']

            text.type = Marker.TEXT_VIEW_FACING
            text.action = Marker.ADD

            text.pose.position.x = node['x']
            text.pose.position.y = node['y']
            text.pose.position.z = 0.35

            text.pose.orientation.w = 1.0

            text.scale.z = 0.25

            text.color.r = 1.0
            text.color.g = 1.0
            text.color.b = 1.0
            text.color.a = 1.0

            text.text = f'Node {node["id"]}'

            marker_array.markers.append(text)

        # ------------------------------------------------------
        # EDGES
        # ------------------------------------------------------

        for edge in self.edges:

            start = self.nodes[edge['startid']]
            end = self.nodes[edge['endid']]

            line = Marker()

            line.header.frame_id = 'map'
            line.header.stamp = self.get_clock().now().to_msg()

            line.ns = 'edges'
            line.id = 2000 + edge['id']

            line.type = Marker.LINE_STRIP
            line.action = Marker.ADD

            line.scale.x = 0.06

            line.color.r = 0.0
            line.color.g = 0.8
            line.color.b = 1.0
            line.color.a = 1.0

            p1 = PointStamped().point

            p1.x = start['x']
            p1.y = start['y']
            p1.z = 0.05

            p2 = PointStamped().point

            p2.x = end['x']
            p2.y = end['y']
            p2.z = 0.05

            line.points.append(p1)
            line.points.append(p2)

            marker_array.markers.append(line)

        self.marker_pub.publish(marker_array)

    # ==========================================================
    # SAVE GEOJSON
    # ==========================================================

    def save_geojson(self):

        # Jangan save kalau masih ada node pending
        if self.pending_node_id is not None:

            self.get_logger().warn(
                f'Node {self.pending_node_id} belum '
                'dikonfirmasi. Gunakan k atau r.'
            )
            return

        features = []

        # ------------------------------------------------------
        # NODE FEATURES
        # ------------------------------------------------------

        for node in self.nodes:

            features.append({
                "type": "Feature",
                "properties": {
                    "id": node["id"],
                    "frame": "map"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        node["x"],
                        node["y"]
                    ]
                }
            })

        # ------------------------------------------------------
        # EDGE FEATURES
        # ------------------------------------------------------

        for edge in self.edges:

            start = self.nodes[edge["startid"]]
            end = self.nodes[edge["endid"]]

            features.append({
                "type": "Feature",
                "properties": {
                    "id": len(self.nodes) + edge["id"],
                    "startid": edge["startid"],
                    "endid": edge["endid"]
                },
                "geometry": {
                    "type": "MultiLineString",
                    "coordinates": [[
                        [
                            start["x"],
                            start["y"]
                        ],
                        [
                            end["x"],
                            end["y"]
                        ]
                    ]]
                }
            })

        geojson = {
            "type": "FeatureCollection",
            "name": "graph",
            "features": features
        }

        os.makedirs(
            os.path.dirname(self.output_file),
            exist_ok=True
        )

        with open(
            self.output_file,
            'w'
        ) as f:

            json.dump(
                geojson,
                f,
                indent=4
            )

        self.get_logger().info('======================================')
        self.get_logger().info('GeoJSON berhasil disimpan!')
        self.get_logger().info(self.output_file)
        self.get_logger().info(
            f'Nodes : {len(self.nodes)}'
        )
        self.get_logger().info(
            f'Edges : {len(self.edges)}'
        )
        self.get_logger().info('======================================')

    # ==========================================================
    # RESET
    # ==========================================================

    def reset(self):

        self.nodes.clear()
        self.edges.clear()

        self.pending_node_id = None

        self.publish_markers()

        self.get_logger().info(
            'Semua node dan edge telah dihapus.'
        )

    # ==========================================================
    # KEYBOARD
    # ==========================================================

    def keyboard_loop(self):

        while rclpy.ok():

            try:

                command = input(
                    '\nCommand [k/r/e/s/l/q]: '
                ).strip().lower()

                # ----------------------------------------------
                # KEEP NODE
                # ----------------------------------------------

                if command == 'k':

                    self.keep_node()

                # ----------------------------------------------
                # MANUAL EDIT NODE
                # ----------------------------------------------

                elif command == 'r':

                    # Jika ada pending node,
                    # r = rapikan manual
                    if self.pending_node_id is not None:

                        self.manual_edit_node()

                    else:

                        # Kalau tidak ada pending node,
                        # r = reset
                        self.reset()

                # ----------------------------------------------
                # CREATE EDGE
                # ----------------------------------------------

                elif command == 'e':

                    self.create_edge_interactive()

                # ----------------------------------------------
                # SAVE
                # ----------------------------------------------

                elif command == 's':

                    self.save_geojson()

                # ----------------------------------------------
                # LIST
                # ----------------------------------------------

                elif command == 'l':

                    self.show_graph()

                # ----------------------------------------------
                # QUIT
                # ----------------------------------------------

                elif command == 'q':

                    self.get_logger().info(
                        'Route editor berhenti.'
                    )

                    rclpy.shutdown()
                    break

                else:

                    print(
                        'Command tidak dikenal.'
                    )

            except EOFError:

                break

            except KeyboardInterrupt:

                break

    # ==========================================================


def main(args=None):

    rclpy.init(args=args)

    node = RouteEditor()

    try:

        rclpy.spin(node)

    except KeyboardInterrupt:

        pass

    finally:

        node.destroy_node()

        if rclpy.ok():

            rclpy.shutdown()


if __name__ == '__main__':
    main()