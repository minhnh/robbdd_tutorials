"""Configured observation evaluators used by the tutorial models."""

from rdflib import URIRef

from bdd_exec_ros2.observation import PlanarContainmentEvaluator


_ENV = "https://secorolab.github.io/models/environments/pick-place-single/"

# The collision walls leave an approximately 0.23 m by 0.19 m interior.
# Insetting it by the cube's 0.02 m half-width tests the whole cube footprint.
cube_inside_bin = PlanarContainmentEvaluator(
    URIRef(f"{_ENV}cube"),
    URIRef(f"{_ENV}bin-ws"),
    boundary_size_xy=(0.23, 0.19),
    margin_m=0.02,
)
