import json
import logging
from typing import Any, Dict

class FilterProcessorPipeline:
    def __init__(self):
        self.processors = []

    def append(self, processor):
        self.processors.append(processor)

    def __iadd__(self, processor):
        self.append(processor)
        return self

    def _normalize_filter_values(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        normalized = {}
        for k, v in filters.items():
            logging.debug(f"[FilterProcessorPipeline] Normalizing filter key '{k}' with value: {v}")
            if isinstance(v, str):
                try:
                    normalized_value = json.loads(v)
                    logging.debug(f"[FilterProcessorPipeline] Parsed stringified value for '{k}': {normalized_value}")
                    normalized[k] = normalized_value
                except Exception as e:
                    logging.debug(f"[FilterProcessorPipeline] Could not parse stringified filter value for '{k}': {v} (Error: {e})")
                    normalized[k] = v
            else:
                normalized[k] = v
        return normalized

    def run(self, data: Any) -> dict:
        if isinstance(data, str):
            data = {"question": data}
            logging.debug(f"[FilterProcessorPipeline] Wrapped string input into dict: {data}")

        for processor in self.processors:
            logging.debug(f"[FilterProcessorPipeline] Running processor: {processor.__class__.__name__}")
            data = processor.process(data)
            logging.debug(f"[FilterProcessorPipeline] Data after {processor.__class__.__name__}: {data}")

            if "filters" in data and isinstance(data["filters"], dict):
                logging.debug(f"[FilterProcessorPipeline] Normalizing filters after {processor.__class__.__name__}")
                data["filters"] = self._normalize_filter_values(data["filters"])

        logging.debug(f"[FilterProcessorPipeline] Final data after all processors: {data}")
        return data
