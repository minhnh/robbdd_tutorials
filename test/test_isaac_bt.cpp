// Copyright 2026 Minh Nguyen
// SPDX-License-Identifier: Apache-2.0
#include <bdd_bt_executor_ros2/nodes/apply_planning_scene.hpp>
#include <bdd_bt_executor_ros2/nodes/build_planning_scene.hpp>
#include <bdd_bt_executor_ros2/nodes/planning_scene_objects.hpp>
#include <bdd_bt_executor_ros2/nodes/mock_timed_action.hpp>
#include <bdd_bt_executor_ros2/nodes/motion_actions.hpp>
#include <bdd_bt_executor_ros2/nodes/wait_for_moveit_ready.hpp>
#include <bdd_bt_executor_ros2/nodes/pose_operations.hpp>
#include <bdd_bt_executor_ros2/nodes/resolve_behaviour_parameters.hpp>
#include <behaviortree_cpp/bt_factory.h>
#include <gtest/gtest.h>
#include <thread>

using namespace bdd_bt_executor_ros2;
using Behaviour = bdd_ros2_interfaces::action::Behaviour;

TEST(IsaacTutorial, ShippedTreeRemovesAndRestoresSelectedObject)
{
    rclcpp::init(0, nullptr);
    {
        const auto config    = YAML::LoadFile(TUTORIAL_CONFIG);
        const auto catalogue = readSceneEntities(config);
        auto       node      = std::make_shared<rclcpp::Node>("test_tutorial_scene");
        rclcpp::executors::SingleThreadedExecutor executor;
        executor.add_node(node);
        std::vector<moveit_msgs::msg::PlanningScene> requests;
        auto service = node->create_service<ApplyPlanningScene::Service>(
          "/test_isaac_bt/apply_planning_scene",
          [&](
            const ApplyPlanningScene::Service::Request::SharedPtr request,
            ApplyPlanningScene::Service::Response::SharedPtr      response
          ) {
              requests.push_back(request->scene);
              response->success = true;
          }
        );
        using Query = moveit_msgs::srv::GetPlanningScene;
        moveit_msgs::msg::PlanningScene current;
        auto                            query_service = node->create_service<Query>(
          "/test_isaac_bt/get_planning_scene",
          [&](const Query::Request::SharedPtr, Query::Response::SharedPtr response) {
              response->scene = current;
          }
        );
        auto entity_service = node->create_service<GetEntityPose::Service>(
          "/test_isaac_bt/get_entity_state",
          [&](
            const GetEntityPose::Service::Request::SharedPtr request,
            GetEntityPose::Service::Response::SharedPtr      response
          ) {
              response->result.result            = response->result.RESULT_OK;
              response->state.header.frame_id    = "entity_frame";
              response->state.pose.orientation.w = 1;
              if (request->entity == "/spawned/bottle") response->state.pose.position.x = 1.25;
          }
        );
        BT::BehaviorTreeFactory factory;
        factory.registerNodeType<ResolveBehaviourParameters>("ResolveBehaviourParameters");
        factory.registerNodeType<SelectEntityPose>("SelectEntityPose");
        factory.registerNodeType<OffsetPose>("OffsetPose");
        factory.registerNodeType<ClearPlanningSceneForUris>("ClearPlanningSceneForUris", node);
        factory.registerNodeType<GetEntityPoses>("GetEntityPoses", node);
        factory.registerNodeType<BuildPlanningScene>("BuildPlanningScene");
        factory.registerNodeType<ApplyPlanningScene>("ApplyPlanningScene", node);
        factory.registerBuilder<MockTimedAction>(
          "MockTimedAction", [node](const std::string &name, const BT::NodeConfig &config) {
              auto test_config = config;
              // Skip the human inspection delay in the offline test.
              test_config.input_ports["duration"] = "0";
              return std::make_unique<MockTimedAction>(name, test_config, node);
          }
        );
        // Generic readiness checks are covered in the executor tests.
        factory.registerSimpleAction(
          "WaitForMoveItReady",
          [](BT::TreeNode &) { return BT::NodeStatus::SUCCESS; },
          WaitForMoveItReady::providedPorts()
        );
        bool                     planned       = false;
        bool                     planning_only = true;
        std::vector<std::string> motion_steps;
        factory.registerSimpleAction(
          "MoveGroupAction",
          [&](BT::TreeNode &action) {
              EXPECT_EQ(action.getInput<bool>("plan_only").value(), planning_only);
              motion_steps.push_back(std::string(action.getRawPortValue("target_pose")));
              EXPECT_EQ(action.getInput<std::string>("group").value(), "panda_arm");
              EXPECT_FALSE(action.getInput<geometry_msgs::msg::PoseStamped>("target_pose")
                             .value()
                             .header.frame_id.empty());
              planned = true;
              return BT::NodeStatus::SUCCESS;
          },
          MoveGroupAction::providedPorts()
        );
        factory.registerNodeType<AttachObjectByUri>("AttachObjectByUri");
        factory.registerNodeType<DetachObjectByUri>("DetachObjectByUri");
        factory.registerSimpleAction(
          "GripperCommandAction",
          [&](BT::TreeNode &action) {
              motion_steps.push_back(
                action.getInput<double>("position").value() == 0 ? "close" : "open"
              );
              return BT::NodeStatus::SUCCESS;
          },
          GripperCommandAction::providedPorts()
        );
        factory.registerBehaviorTreeFromFile(TUTORIAL_PLAN_TREE);
        auto bb = BT::Blackboard::create();
        for (const auto &[key, value] : std::map<std::string, std::string>{
               { "config_file", TUTORIAL_CONFIG },
               { "group", "panda_arm" },
               { "pick_clearance", "0;0;0.1" },
               { "place_clearance", "0;0;0.2" },
               { "end_effector_frame", "panda_hand" },
               { "move_group_action", "/move_action" },
               { "gripper_action", "/gripper_cmd" },
               { "touch_links", "hand;leftfinger;rightfinger" },
               { "target_frame", "world" },
               { "world_frame", "world" },
               { "simulation_namespace", "/test_isaac_bt" },
               { "timeout", "5" },
               { "planning_scene_service", "/test_isaac_bt/apply_planning_scene" },
               { "planning_scene_query", "/test_isaac_bt/get_planning_scene" },
               { "expected_robot_uri",
                 "https://secorolab.github.io/models/agents/pick-place-single/panda" } })
            bb->set(key, value);
        auto                           goal = std::make_shared<Behaviour::Goal>();
        const std::vector<std::string> values{ catalogue.back().uri,
                                               catalogue[2].uri,
                                               bb->get<std::string>("expected_robot_uri") };
        size_t                         i = 0;
        for (auto role : { "object_uri", "place_workspace_uri", "robot_uri" }) {
            bdd_ros2_interfaces::msg::ParamValue binding;
            binding.variable_uri   = config["variable_bindings"][role].as<std::string>();
            binding.param_val_uris = { values[i++] };
            goal->parameters.push_back(binding);
        }
        bb->set("behaviour_goal", std::shared_ptr<const Behaviour::Goal>(goal));
        const auto &bottle = catalogue.back();
        current.world.collision_objects.push_back(bottle.object);
        auto tree = factory.createTree("InspectResolvedObject", bb);
        auto run  = [&] {
            const auto     end    = std::chrono::steady_clock::now() + std::chrono::seconds(8);
            BT::NodeStatus status = BT::NodeStatus::RUNNING;
            do {
                executor.spin_some();
                status = tree.tickOnce();
                if (status != BT::NodeStatus::RUNNING) return status;
                std::this_thread::sleep_for(std::chrono::milliseconds(5));
            } while (std::chrono::steady_clock::now() < end);
            tree.haltTree();
            return status;
        };
        ASSERT_EQ(run(), BT::NodeStatus::SUCCESS);
        ASSERT_EQ(requests.size(), 4u);
        ASSERT_EQ(requests[2].world.collision_objects.size(), 1u);
        EXPECT_EQ(requests[2].world.collision_objects[0].id, bottle.object.id);
        EXPECT_EQ(
          requests[2].world.collision_objects[0].operation,
          moveit_msgs::msg::CollisionObject::REMOVE
        );
        ASSERT_EQ(requests[3].world.collision_objects.size(), catalogue.size());
        EXPECT_EQ(requests[3].world.collision_objects.back().id, bottle.object.id);
        EXPECT_DOUBLE_EQ(requests[3].world.collision_objects.back().pose.position.x, 1.25);
        tree = factory.createTree("PlanApproach", bb);
        ASSERT_EQ(run(), BT::NodeStatus::SUCCESS);
        EXPECT_TRUE(planned);
        factory.clearRegisteredBehaviorTrees();
        factory.registerBehaviorTreeFromFile(TUTORIAL_MOTION_TREE);
        planning_only = false;
        motion_steps.clear();
        tree = factory.createTree("PickPlace", bb);
        ASSERT_EQ(run(), BT::NodeStatus::SUCCESS);
        EXPECT_EQ(
          motion_steps,
          (std::vector<std::string>{ "open",
                                     "{pre_pick_pose}",
                                     "{pick_pose}",
                                     "close",
                                     "{post_pick_pose}",
                                     "{pre_place_pose}",
                                     "{place_pose}",
                                     "open",
                                     "{post_place_pose}" })
        );
    }
    rclcpp::shutdown();
}
