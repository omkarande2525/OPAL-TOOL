import structlog
from typing import List, Optional
from pydantic import BaseModel

from autodataset.models.specifications import DatasetSpecification, DataSource, SourceType, DataFormat

logger = structlog.get_logger()

class SourceResolutionResult(BaseModel):
    primary_source: DataSource
    fallback_sources: List[DataSource]

class SourceResolver:
    def __init__(self):
        # Trusted Source Registry mapping domains to curated, robust APIs
        self.registry = {
            "healthcare": [
                {
                    "source": DataSource(
                        source_id="fda_open_data",
                        source_type=SourceType.API,
                        location="https://api.fda.gov/drug/event.json?limit=100",
                        format=DataFormat.JSON
                    ),
                    "reliability_score": 0.95,
                    "structured": True
                },
                {
                    "source": DataSource(
                        source_id="who_athena",
                        source_type=SourceType.API,
                        location="https://ghoapi.azureedge.net/api/Indicator",
                        format=DataFormat.JSON
                    ),
                    "reliability_score": 0.90,
                    "structured": True
                }
            ],
            "finance": [
                {
                    "source": DataSource(
                        source_id="worldbank_indicators",
                        source_type=SourceType.API,
                        location="https://api.worldbank.org/v2/country/all/indicator/SP.POP.TOTL?format=json",
                        format=DataFormat.JSON
                    ),
                    "reliability_score": 0.98,
                    "structured": True
                }
            ],
            "general": [
                {
                    "source": DataSource(
                        source_id="data_gov_catalog",
                        source_type=SourceType.API,
                        location="https://catalog.data.gov/api/3/action/package_search",
                        format=DataFormat.JSON
                    ),
                    "reliability_score": 0.85,
                    "structured": True
                },
                {
                    "source": DataSource(
                        source_id="jsonplaceholder",
                        source_type=SourceType.API,
                        location="https://jsonplaceholder.typicode.com/users",
                        format=DataFormat.JSON
                    ),
                    "reliability_score": 0.80,
                    "structured": True
                }
            ]
        }

    def resolve(self, spec: DatasetSpecification) -> SourceResolutionResult:
        logger.info("Resolving sources for specification", spec_id=spec.spec_id, domain=spec.domain)

        # Manual Mode: If user explicitly provided sources, we respect them.
        if spec.data_sources and len(spec.data_sources) > 0:
            logger.info("Manual mode active: Using explicitly provided data sources", count=len(spec.data_sources))
            return SourceResolutionResult(
                primary_source=spec.data_sources[0],
                fallback_sources=spec.data_sources[1:]
            )

        # Auto Mode: System intelligently resolves the source
        domain = spec.domain.lower()
        candidates = self.registry.get(domain, [])

        if not candidates:
            if domain == "healthcare":
                # Strict enforcement for high-risk domains
                logger.error("Strict domain violation: no valid healthcare sources found")
                raise ValueError(f"Strict domain enforcement failed: No authoritative sources found for {domain}")
            
            # Safe fallback for unknown domains to general trusted APIs
            logger.warning("Unknown domain, falling back to general trusted APIs", domain=domain)
            candidates = self.registry.get("general", [])

        if not candidates:
            raise ValueError(f"No valid sources could be resolved for domain: {domain}")

        # Rank sources prioritizing highest reliability, then structured boolean
        candidates.sort(key=lambda x: (x["reliability_score"], x["structured"]), reverse=True)
        
        primary = candidates[0]["source"]
        fallbacks = [c["source"] for c in candidates[1:]]

        logger.info(
            "Source resolution complete", 
            primary_source=primary.source_id, 
            fallback_count=len(fallbacks)
        )

        return SourceResolutionResult(
            primary_source=primary,
            fallback_sources=fallbacks
        )
