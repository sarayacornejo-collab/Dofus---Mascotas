"""Configuración compartida del bot de tendencias PRL/SST."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

NICHE = "Prevención de Riesgos Laborales (PRL/SST) en LATAM y España"

SEED_KEYWORDS: list[str] = [
    "prevención riesgos laborales",
    "seguridad laboral",
    "salud ocupacional",
    "accidente laboral",
    "EPP equipos protección personal",
    "ergonomía trabajo",
    "estrés laboral",
    "riesgos psicosociales",
    "trabajo en altura",
    "espacios confinados",
    "primeros auxilios trabajo",
    "capacitación seguridad",
    "norma ISO 45001",
    "comité paritario",
    "plan de emergencia",
]

REGION_LABELS: dict[str, str] = {
    "ES": "España",
    "MX": "México",
    "AR": "Argentina",
    "CO": "Colombia",
    "CL": "Chile",
    "PE": "Perú",
    "EC": "Ecuador",
    "UY": "Uruguay",
    "DO": "República Dominicana",
}


@dataclass
class Settings:
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    youtube_api_key: str | None = field(default_factory=lambda: os.getenv("YOUTUBE_API_KEY") or None)
    regions: list[str] = field(
        default_factory=lambda: [
            r.strip().upper()
            for r in (os.getenv("DEFAULT_REGIONS") or "ES,MX,AR,CO,CL,PE").split(",")
            if r.strip()
        ]
    )
    timeframe: str = field(default_factory=lambda: os.getenv("DEFAULT_TIMEFRAME", "now 7-d"))
    model: str = field(default_factory=lambda: os.getenv("CLAUDE_MODEL", "claude-opus-4-7"))

    def validate(self) -> list[str]:
        problems: list[str] = []
        if not self.anthropic_api_key:
            problems.append("ANTHROPIC_API_KEY no definida — el análisis no se puede ejecutar.")
        unknown = [r for r in self.regions if r not in REGION_LABELS]
        if unknown:
            problems.append(f"Regiones desconocidas (revisa códigos ISO): {unknown}")
        return problems
