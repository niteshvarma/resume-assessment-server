from dataclasses import dataclass
from typing import Union, Dict, List, Any

# @dataclass
# class MetadataFilter:
#     key: str
#     value: Union[str, List[str], Dict[str, Any]]

#     def to_pinecone_filter(self) -> Dict[str, Any]:
#         """
#         Converts this filter into a Pinecone-compatible format.
#         Handles value types:
#         - String: Direct equality match.
#         - List (as OR condition using `$in`).
#         - Dict with range operators (e.g., {"min": 5, "max": 10}).
#         """
#         if isinstance(self.value, str):
#             # Direct match for a single string
#             return {self.key: self.value}

#         elif isinstance(self.value, list):
#             if not all(isinstance(item, str) for item in self.value):
#                 raise ValueError(f"Expected all list items to be strings for key '{self.key}', got: {self.value}")
#             if len(self.value) == 1:
#                 return {self.key: self.value[0]}
#             return {self.key: {"$in": self.value}}
        
#         elif isinstance(self.value, dict):
#             # Handle numeric range filter (e.g., years_experience: {min: 5, max: 7})
#             range_filter = {}
#             if "min" in self.value:
#                 range_filter["$gte"] = self.value["min"]
#             if "max" in self.value:
#                 range_filter["$lte"] = self.value["max"]
#             return {self.key: range_filter}

#         else:
#             # If the value type is unsupported, raise an error
#             raise ValueError(f"Unsupported value type for metadata filter: {self.value}")

from dataclasses import dataclass
from typing import Union, List, Dict, Any
from enum import Enum


class FilterOperator(str, Enum):
    EQ = "$eq"
    IN = "$in"
    GTE = "$gte"
    LTE = "$lte"


@dataclass
class MetadataFilter:
    key: str
    value: Union[str, int, float, List[str], Dict[str, Any]]
    operator: FilterOperator = FilterOperator.EQ  # default to equality

    def to_pinecone_filter(self) -> Dict[str, Any]:
        """
        Converts this filter into a Pinecone-compatible format.
        Supports:
        - EQ (default): { key: value }
        - IN: { key: { "$in": [...] } }
        - GTE / LTE: { key: { "$gte": value } } or { key: { "$lte": value } }
        """
        if self.operator == FilterOperator.EQ:
            return {self.key: self.value}

        elif self.operator == FilterOperator.IN:
            if not isinstance(self.value, list) or not all(isinstance(v, str) for v in self.value):
                raise ValueError(f"IN operator expects a list of strings, got: {self.value}")
            return {self.key: {"$in": self.value}}

        elif self.operator in (FilterOperator.GTE, FilterOperator.LTE):
            if not isinstance(self.value, (int, float)):
                raise ValueError(f"{self.operator} operator expects a numeric value, got: {self.value}")
            return {self.key: {self.operator.value: self.value}}

        else:
            raise ValueError(f"Unsupported operator: {self.operator}")

