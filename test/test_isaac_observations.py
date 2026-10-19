"""Load the shipped Isaac models and check the Panda role binding."""

from pathlib import Path

import yaml
from bdd_exec_ros2.conversions import get_bhv_param_messages

from bdd_dsl.models.user_story import UserStoryLoader
from bdd_dsl.models.variation import get_task_var_dicts
from rdf_utils.resolver import install_resolver
from rdf_utils.models.vocab import URI_EXEC_PRED_RUNS_SCENE
from rdflib import Graph, URIRef
from robbdd.rdf.bdd import create_bdd_model_graph
from robbdd.rdf.bddx import create_bddx_model_graph
from textx import metamodel_for_file


def test_isaac_models_load_with_panda_binding():
    install_resolver()
    root = Path(__file__).parents[1] / "models" / "pick_place"
    graph = Graph()
    for filename, build in (
        ("common/pick_place.bdd", create_bdd_model_graph),
        ("isaacsim/pick_place.bdd", create_bdd_model_graph),
        ("isaacsim/pick_place.bddx", create_bddx_model_graph),
    ):
        path = str(root / filename)
        build(model=metamodel_for_file(path).model_from_file(path), g=graph)
    loader = UserStoryLoader(graph, shacl_check=False)
    story = URIRef("https://secorolab.github.io/robbdd/tutorials/pick-place/isaac/isaac-pick-place-story")
    variant = loader.load_scenario_variant(graph, next(iter(loader.get_us_scenario_variants()[story])))
    values = get_task_var_dicts(variant.task_variation)[0]
    assert not variant.scene.agents
    robot = URIRef("https://secorolab.github.io/robbdd/tutorials/pick-place/var-robot")
    assert values[robot] == URIRef(
        "https://secorolab.github.io/models/agents/pick-place-single/panda"
    )

    parameters = get_bhv_param_messages(variant.when_bhv_model, values)
    config = Path(__file__).parents[1] / "config" / "isaac_pick_place.yaml"
    required = yaml.safe_load(config.read_text())["variable_bindings"]
    assert set(required.values()) <= {p.variable_uri for p in parameters}

    execution = URIRef(
        "https://secorolab.github.io/robbdd/tutorials/pick-place/isaac/execution/isaac-pick-place"
    )
    assert graph.value(execution, URI_EXEC_PRED_RUNS_SCENE) == URIRef(
        "https://secorolab.github.io/models/scenes/pick-place-positive-isaac/pick_place_scene_isaac"
    )
