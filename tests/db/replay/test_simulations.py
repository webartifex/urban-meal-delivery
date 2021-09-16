"""Test the ORM's `ReplaySimulation` model."""


class TestSpecialMethods:
    """Test special methods in `ReplaySimulation`."""

    def test_create_simulation(self, simulation):
        """Test instantiation of a new `ReplaySimulation` object."""
        assert simulation is not None

    def test_text_representation(self, simulation):
        """`ReplaySimulation` has a non-literal text representation."""
        result = repr(simulation)

        assert result.startswith('<ReplaySimulation(')
        assert simulation.city.name in result
        assert simulation.strategy in result
