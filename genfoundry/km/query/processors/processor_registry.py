from genfoundry.km.query.processors.geo_expansion_processor import GeoExpansionProcessor
from genfoundry.km.query.processors.base_filter_processor import BaseFilterProcessor
from genfoundry.km.query.processors.processor_pipeline import FilterProcessorPipeline


PROCESSOR_REGISTRY = {
    "BaseFilterProcessor": BaseFilterProcessor,  # Placeholder for the base processor
    "GeoExpansionProcessor": GeoExpansionProcessor,
    # add others here
}

def build_processor_pipeline(processor_names: list[str]) -> FilterProcessorPipeline:
    pipeline = FilterProcessorPipeline()
    for name in processor_names:
        cls = PROCESSOR_REGISTRY.get(name)
        if cls:
            pipeline += cls()
        else:
            raise ValueError(f"Processor '{name}' not found in registry")
    return pipeline