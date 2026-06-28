# NewsBrief Plan A: Core Pipeline Implementation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Python foundation that reads CDB data from MySQL, generates a narration script via Claude, formats numbers for speech, and produces the intermediate data structures all downstream stages consume.

**Architecture:** Python orchestrator with stage-based pipeline. Each stage is a module in `src/stages/`. Shared libraries in `src/lib/`. Configuration via `.env` + YAML. SQLAlchemy for DB access. Anthropic SDK for LLM calls. All stages are independently testable functions that accept typed inputs and return typed outputs.

**Tech Stack:** Python 3.11+, SQLAlchemy 2.0, PyMySQL, anthropic SDK, python-dotenv, PyYAML, structlog, Jinja2, pytest

**Related Plans:**
- Plan B: Audio + Spec (ElevenLabs, pronunciation, spec builder)
- Plan C: Remotion Renderer (Node/TypeScript visual templates)
- Plan D: Distribution + Operations (uploads, health checks, CLI)

---

## File Structure

```
/Users/arthurbillingsley/Downloads/Projects/NewsBrief/
  .env.example                    # Template for credentials (committed)
  .gitignore
  requirements.txt
  pytest.ini
  src/
    __init__.py
    run.py                        # Main orchestrator entry point
    config.py                     # Settings loader (.env + YAML)
    models.py                     # SQLAlchemy ORM models (read-only CDB + new video tables)
    stages/
      __init__.py
      extract.py                  # Stage 1: Read clusters, assert date
      script.py                   # Stage 2: LLM script generation
      format_speech.py            # Stage 2b: Number-to-speech conversion
    lib/
      __init__.py
      db.py                       # Database connection factory + session management
      retry.py                    # Exponential backoff with jitter
  migrations/
    006_create_video_tables.sql   # Schema migration
  config/
    pronunciation.yaml            # SSML dictionary (placeholder for Plan B)
  tests/
    __init__.py
    conftest.py                   # Shared fixtures (DB session, sample data)
    test_config.py
    test_models.py
    test_extract.py
    test_script.py
    test_format_speech.py
    test_retry.py
    test_run.py
```

---

### Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `pytest.ini`
- Create: `src/__init__.py`
- Create: `src/stages/__init__.py`
- Create: `src/lib/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Initialize git repo and create .gitignore**

```bash
cd /Users/arthurbillingsley/Downloads/Projects/NewsBrief
git init
```

Create `.gitignore`:

```
__pycache__/
*.pyc
.env
*.egg-info/
dist/
build/
.venv/
.pytest_cache/
tmp/
logs/
config/gdrive-sa-key.json
node_modules/
```

- [ ] **Step 2: Create requirements.txt**

```
# Database
SQLAlchemy>=2.0,<3.0
PyMySQL>=1.1,<2.0
cryptography>=42.0,<44.0

# AI / LLM
anthropic>=0.40,<1.0

# Configuration
python-dotenv>=1.0,<2.0
PyYAML>=6.0,<7.0

# Observability
structlog>=24.0,<25.0

# Templates
jinja2>=3.1,<4.0

# Utilities
python-dateutil>=2.9,<3.0

# Testing
pytest>=8.0,<9.0
pytest-mock>=3.12,<4.0
```

- [ ] **Step 3: Create .env.example**

```bash
# Database (CDB pipeline RDS)
DB_HOST=cifaas-prod-db.c6him66imu2d.us-east-1.rds.amazonaws.com
DB_PORT=3306
DB_USER=cdb
DB_PASSWORD=changeme
DB_NAME=cdb

# Claude API (script generation)
ANTHROPIC_API_KEY=sk-ant-changeme

# ElevenLabs (Plan B)
ELEVENLABS_API_KEY=changeme
ELEVENLABS_VOICE_ID=changeme

# Publish gate (R1)
PUBLISH_MODE=preview

# Alerting
ALERT_EMAIL_TO=arthur@cognoscerellc.com
ALERT_EMAIL_FROM=newsbrief@cognoscerellc.com
```

- [ ] **Step 4: Create pytest.ini**

```ini
[pytest]
testpaths = tests
pythonpath = .
```

- [ ] **Step 5: Create package init files**

Create empty `src/__init__.py`, `src/stages/__init__.py`, `src/lib/__init__.py`, `tests/__init__.py`.

- [ ] **Step 6: Create virtual environment and install deps**

```bash
cd /Users/arthurbillingsley/Downloads/Projects/NewsBrief
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run: `python -c "import sqlalchemy; print(sqlalchemy.__version__)"`
Expected: `2.x.x`

- [ ] **Step 7: Commit**

```bash
git add .gitignore requirements.txt .env.example pytest.ini src/__init__.py src/stages/__init__.py src/lib/__init__.py tests/__init__.py
git commit -m "feat: project scaffolding with deps, config template, and test setup"
```

---

### Task 2: Configuration Loader

**Files:**
- Create: `src/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
import os
import pytest
from unittest.mock import patch


def test_config_loads_db_settings_from_env():
    env = {
        "DB_HOST": "localhost",
        "DB_PORT": "3306",
        "DB_USER": "testuser",
        "DB_PASSWORD": "testpass",
        "DB_NAME": "testdb",
        "ANTHROPIC_API_KEY": "sk-ant-test",
        "PUBLISH_MODE": "preview",
    }
    with patch.dict(os.environ, env, clear=False):
        from src.config import load_config

        cfg = load_config()
        assert cfg.db_host == "localhost"
        assert cfg.db_port == 3306
        assert cfg.db_user == "testuser"
        assert cfg.db_name == "testdb"
        assert cfg.anthropic_api_key == "sk-ant-test"
        assert cfg.publish_mode == "preview"


def test_config_defaults_publish_mode_to_preview():
    env = {
        "DB_HOST": "localhost",
        "DB_PORT": "3306",
        "DB_USER": "testuser",
        "DB_PASSWORD": "testpass",
        "DB_NAME": "testdb",
        "ANTHROPIC_API_KEY": "sk-ant-test",
    }
    with patch.dict(os.environ, env, clear=False):
        from src.config import load_config

        cfg = load_config()
        assert cfg.publish_mode == "preview"


def test_config_raises_on_missing_required_key():
    env = {"DB_HOST": "localhost"}  # missing most required keys
    with patch.dict(os.environ, env, clear=True):
        from src.config import load_config

        with pytest.raises(ValueError, match="DB_USER"):
            load_config()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/arthurbillingsley/Downloads/Projects/NewsBrief && .venv/bin/pytest tests/test_config.py -v`
Expected: FAIL (ImportError — `src.config` does not exist)

- [ ] **Step 3: Write minimal implementation**

```python
# src/config.py
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    # Database
    db_host: str
    db_port: int
    db_user: str
    db_password: str
    db_name: str

    # Claude API
    anthropic_api_key: str

    # ElevenLabs (used in Plan B)
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""

    # Publish gate
    publish_mode: str = "preview"  # preview | gate | auto

    # Alerting
    alert_email_to: str = ""
    alert_email_from: str = ""

    @property
    def db_url(self) -> str:
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


_REQUIRED = ["DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME", "ANTHROPIC_API_KEY"]


def load_config() -> Config:
    load_dotenv()
    missing = [k for k in _REQUIRED if not os.environ.get(k)]
    if missing:
        raise ValueError(f"Missing required env vars: {', '.join(missing)}")

    return Config(
        db_host=os.environ["DB_HOST"],
        db_port=int(os.environ["DB_PORT"]),
        db_user=os.environ["DB_USER"],
        db_password=os.environ["DB_PASSWORD"],
        db_name=os.environ["DB_NAME"],
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        elevenlabs_api_key=os.environ.get("ELEVENLABS_API_KEY", ""),
        elevenlabs_voice_id=os.environ.get("ELEVENLABS_VOICE_ID", ""),
        publish_mode=os.environ.get("PUBLISH_MODE", "preview"),
        alert_email_to=os.environ.get("ALERT_EMAIL_TO", ""),
        alert_email_from=os.environ.get("ALERT_EMAIL_FROM", ""),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_config.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/config.py tests/test_config.py
git commit -m "feat: configuration loader from .env with validation"
```

---

### Task 3: Retry Utility

**Files:**
- Create: `src/lib/retry.py`
- Create: `tests/test_retry.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_retry.py
import pytest
from unittest.mock import MagicMock, patch


def test_retry_returns_on_first_success():
    from src.lib.retry import retry_with_backoff

    fn = MagicMock(return_value="ok")
    result = retry_with_backoff(fn, max_retries=3, base_delay=0.01)
    assert result == "ok"
    assert fn.call_count == 1


def test_retry_retries_on_failure_then_succeeds():
    from src.lib.retry import retry_with_backoff

    fn = MagicMock(side_effect=[ValueError("fail"), ValueError("fail"), "ok"])
    result = retry_with_backoff(fn, max_retries=3, base_delay=0.01)
    assert result == "ok"
    assert fn.call_count == 3


def test_retry_raises_after_max_retries():
    from src.lib.retry import retry_with_backoff

    fn = MagicMock(side_effect=ValueError("always fails"))
    with pytest.raises(ValueError, match="always fails"):
        retry_with_backoff(fn, max_retries=2, base_delay=0.01)
    assert fn.call_count == 3  # initial + 2 retries


def test_retry_respects_specific_exception_types():
    from src.lib.retry import retry_with_backoff

    fn = MagicMock(side_effect=TypeError("wrong type"))
    with pytest.raises(TypeError):
        retry_with_backoff(fn, max_retries=3, base_delay=0.01, retry_on=(ValueError,))
    assert fn.call_count == 1  # no retry for TypeError
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_retry.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Write minimal implementation**

```python
# src/lib/retry.py
from __future__ import annotations

import random
import time
from typing import Any, Callable, Tuple, Type


def retry_with_backoff(
    fn: Callable[[], Any],
    max_retries: int = 3,
    base_delay: float = 5.0,
    max_delay: float = 120.0,
    retry_on: Tuple[Type[BaseException], ...] = (Exception,),
) -> Any:
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except retry_on as e:
            if attempt == max_retries:
                raise
            delay = min(base_delay * (2 ** attempt), max_delay)
            jitter = random.uniform(0, delay * 0.25)
            time.sleep(delay + jitter)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_retry.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/lib/retry.py tests/test_retry.py
git commit -m "feat: retry utility with exponential backoff and jitter"
```

---

### Task 4: Database Models (ORM)

**Files:**
- Create: `src/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
from datetime import date, datetime


def test_brief_model_fields():
    from src.models import Brief

    b = Brief(
        id=1,
        issue_number="N103",
        date=date(2026, 6, 10),
        version="v3.2",
        published_at=None,
    )
    assert b.issue_number == "N103"
    assert b.date == date(2026, 6, 10)


def test_cluster_model_fields():
    from src.models import Cluster

    c = Cluster(
        id=1,
        brief_id=1,
        headline="U.S. and Iran Trade Strikes",
        body="Iran shot down...",
        why_this_matters="The Strait carries...",
        what_changed="Iran struck U.S. bases...",
        status="DEVELOPING",
        confidence="High",
        position=1,
    )
    assert c.headline == "U.S. and Iran Trade Strikes"
    assert c.status == "DEVELOPING"
    assert c.position == 1


def test_video_run_model_fields():
    from src.models import VideoRun

    vr = VideoRun(
        id="vr-2026-06-10",
        brief_id=1,
        issue_number="N103",
        run_date=date(2026, 6, 10),
        started_at=datetime(2026, 6, 10, 12, 0, 0),
        status="running",
    )
    assert vr.id == "vr-2026-06-10"
    assert vr.status == "running"


def test_video_script_model_fields():
    from src.models import VideoScript

    vs = VideoScript(
        run_id="vr-2026-06-10",
        brief_id=1,
        hook_copy="An American helicopter is down.",
        lead_copy="Iran shot down a U.S. Army Apache.",
        scan_copy="Four more, fast.",
        why_copy="Here is the thread.",
        close_copy="That is the brief.",
        lead_cluster_id=1,
        scan_cluster_ids=[2, 3, 4, 5],
    )
    assert vs.hook_copy == "An American helicopter is down."
    assert vs.scan_cluster_ids == [2, 3, 4, 5]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_models.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Write minimal implementation**

```python
# src/models.py
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# --- Existing CDB tables (read-only) ---


class Brief(Base):
    __tablename__ = "briefs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    issue_number: Mapped[str] = mapped_column(String(16))
    date: Mapped[date] = mapped_column()
    version: Mapped[str] = mapped_column(String(16))
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    clusters: Mapped[List[Cluster]] = relationship(back_populates="brief", lazy="selectin")


class Cluster(Base):
    __tablename__ = "clusters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    brief_id: Mapped[int] = mapped_column(Integer, ForeignKey("briefs.id"))
    headline: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    why_this_matters: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    what_changed: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    confidence: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)

    brief: Mapped[Brief] = relationship(back_populates="clusters")
    sources: Mapped[List[ClusterSource]] = relationship(back_populates="cluster", lazy="selectin")


class ClusterSource(Base):
    __tablename__ = "cluster_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cluster_id: Mapped[int] = mapped_column(Integer, ForeignKey("clusters.id"))
    source_name: Mapped[str] = mapped_column(String(256))
    source_url: Mapped[str] = mapped_column(Text)

    cluster: Mapped[Cluster] = relationship(back_populates="sources")


# --- New video pipeline tables ---


class VideoRun(Base):
    __tablename__ = "video_runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    brief_id: Mapped[int] = mapped_column(Integer, ForeignKey("briefs.id"))
    issue_number: Mapped[str] = mapped_column(String(16))
    run_date: Mapped[date] = mapped_column()
    started_at: Mapped[datetime] = mapped_column(DateTime(3))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(3), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="running")

    stage_extract_s: Mapped[Optional[Decimal]] = mapped_column(nullable=True)
    stage_script_s: Mapped[Optional[Decimal]] = mapped_column(nullable=True)
    stage_audio_s: Mapped[Optional[Decimal]] = mapped_column(nullable=True)
    stage_spec_s: Mapped[Optional[Decimal]] = mapped_column(nullable=True)
    stage_render_s: Mapped[Optional[Decimal]] = mapped_column(nullable=True)
    stage_post_s: Mapped[Optional[Decimal]] = mapped_column(nullable=True)
    stage_archive_s: Mapped[Optional[Decimal]] = mapped_column(nullable=True)
    total_duration_s: Mapped[Optional[Decimal]] = mapped_column(nullable=True)

    failed_stage: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    stories_selected: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    word_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    audio_duration_s: Mapped[Optional[Decimal]] = mapped_column(nullable=True)

    drive_folder_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    spec_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    elevenlabs_chars: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    llm_input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    llm_output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class VideoScript(Base):
    __tablename__ = "video_scripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(32), ForeignKey("video_runs.id"), unique=True)
    brief_id: Mapped[int] = mapped_column(Integer, ForeignKey("briefs.id"))

    hook_copy: Mapped[str] = mapped_column(Text)
    lead_copy: Mapped[str] = mapped_column(Text)
    scan_copy: Mapped[str] = mapped_column(Text)
    why_copy: Mapped[str] = mapped_column(Text)
    close_copy: Mapped[str] = mapped_column(Text)

    lead_cluster_id: Mapped[int] = mapped_column(Integer, ForeignKey("clusters.id"))
    scan_cluster_ids: Mapped[Any] = mapped_column(JSON)
    selection_rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    platform_meta: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    remotion_spec: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)


class VideoUpload(Base):
    __tablename__ = "video_uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(32), ForeignKey("video_runs.id"))
    platform: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="pending")

    platform_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    platform_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    file_name: Mapped[str] = mapped_column(String(256))
    file_size_bytes: Mapped[Optional[int]] = mapped_column(nullable=True)
    aspect_ratio: Mapped[str] = mapped_column(String(8))
    content_type: Mapped[str] = mapped_column(String(16))
    clip_id: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(3), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(3), nullable=True)
    duration_s: Mapped[Optional[Decimal]] = mapped_column(nullable=True)

    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class PronunciationLog(Base):
    __tablename__ = "pronunciation_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    word: Mapped[str] = mapped_column(String(128), unique=True)
    first_seen_date: Mapped[date] = mapped_column()
    first_seen_run: Mapped[str] = mapped_column(String(32), ForeignKey("video_runs.id"))
    cluster_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    status: Mapped[str] = mapped_column(String(32), default="pending_review")
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(3), nullable=True)
    ssml_markup: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_models.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/models.py tests/test_models.py
git commit -m "feat: SQLAlchemy ORM models for CDB tables and video pipeline tables"
```

---

### Task 5: Database Connection Factory

**Files:**
- Create: `src/lib/db.py`
- Create: `tests/conftest.py`
- Create: `tests/test_db.py` (placeholder — real DB tests are integration)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_db.py
from unittest.mock import patch, MagicMock


def test_get_engine_creates_engine_from_config():
    from src.lib.db import get_engine
    from src.config import Config

    cfg = Config(
        db_host="localhost",
        db_port=3306,
        db_user="test",
        db_password="test",
        db_name="testdb",
        anthropic_api_key="sk-test",
    )
    engine = get_engine(cfg)
    assert "mysql+pymysql" in str(engine.url)
    assert "testdb" in str(engine.url)


def test_get_session_returns_session():
    from src.lib.db import get_engine, get_session
    from src.config import Config

    cfg = Config(
        db_host="localhost",
        db_port=3306,
        db_user="test",
        db_password="test",
        db_name="testdb",
        anthropic_api_key="sk-test",
    )
    engine = get_engine(cfg)
    session = get_session(engine)
    assert session is not None
    session.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_db.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Write minimal implementation**

```python
# src/lib/db.py
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import Config


def get_engine(config: Config) -> Engine:
    return create_engine(
        config.db_url,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False,
    )


def get_session(engine: Engine) -> Session:
    factory = sessionmaker(bind=engine)
    return factory()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_db.py -v`
Expected: 2 passed

- [ ] **Step 5: Create shared test fixtures**

```python
# tests/conftest.py
from datetime import date, datetime

import pytest

from src.config import Config


@pytest.fixture
def sample_config():
    return Config(
        db_host="localhost",
        db_port=3306,
        db_user="test",
        db_password="test",
        db_name="testdb",
        anthropic_api_key="sk-ant-test",
        publish_mode="preview",
    )


@pytest.fixture
def sample_brief_data():
    """Raw dict matching the shape of a Brief + Clusters from the DB."""
    return {
        "brief_id": 1,
        "issue_number": "N103",
        "date": date(2026, 6, 10),
        "clusters": [
            {
                "id": 1,
                "headline": "U.S. and Iran Trade Strikes After Apache Helicopter Downed Near Strait of Hormuz",
                "body": "Iran shot down a U.S. Army Apache helicopter near the Strait of Hormuz...",
                "why_this_matters": "The Strait of Hormuz carries roughly a fifth of the world's oil.",
                "what_changed": "Iran struck U.S. military bases in Bahrain, Jordan, and Kuwait.",
                "status": "DEVELOPING",
                "confidence": "High",
                "position": 1,
                "sources": ["Reuters", "Associated Press", "Wall Street Journal"],
            },
            {
                "id": 2,
                "headline": "Trump and Netanyahu's Iran War Has Stalled, Raising Fears of a Lasting Regional Crisis",
                "body": "A month after the United States and Israel launched joint airstrikes...",
                "why_this_matters": "Oil prices and Strait of Hormuz shipping lanes remain in play.",
                "what_changed": None,
                "status": "NEW",
                "confidence": "High",
                "position": 2,
                "sources": ["BBC News", "The New York Times", "Reuters"],
            },
            {
                "id": 3,
                "headline": "House Sends $70 Billion Immigration Enforcement Bill to Trump",
                "body": "The Republican-controlled House passed a $70 billion immigration enforcement bill...",
                "why_this_matters": "ICE and Border Patrol funded through 2029. No new oversight.",
                "what_changed": None,
                "status": "NEW",
                "confidence": "High",
                "position": 3,
                "sources": ["Reuters", "Associated Press", "Los Angeles Times"],
            },
            {
                "id": 4,
                "headline": "Trump installs housing regulator Bill Pulte as acting intelligence director",
                "body": "President Trump is pressing ahead with his appointment of Bill Pulte...",
                "why_this_matters": "Section 702 surveillance law may lapse this week.",
                "what_changed": None,
                "status": "NEW",
                "confidence": "High",
                "position": 4,
                "sources": ["Reuters", "The Guardian", "Associated Press"],
            },
            {
                "id": 5,
                "headline": 'Trump calls US gas prices "not very high" as national average sits $1 above last year',
                "body": "Gas prices are running about a dollar more per gallon...",
                "why_this_matters": "Filling a 15-gallon tank costs $15 more than a year ago.",
                "what_changed": None,
                "status": "NEW",
                "confidence": "High",
                "position": 5,
                "sources": ["Reuters", "AAA via The Guardian", "Bloomberg"],
            },
            {
                "id": 10,
                "headline": "OpenAI files confidential IPO paperwork with SEC, targeting valuation above $850 billion",
                "body": "OpenAI confirmed Monday it has submitted a confidential S-1 filing...",
                "why_this_matters": "Three of the most valuable private companies are moving to public markets.",
                "what_changed": "OpenAI confirmed its own confidential S-1 filing.",
                "status": "DEVELOPING",
                "confidence": "High",
                "position": 10,
                "sources": ["Reuters", "The Guardian", "Wall Street Journal"],
            },
        ],
    }
```

- [ ] **Step 6: Commit**

```bash
git add src/lib/db.py tests/test_db.py tests/conftest.py
git commit -m "feat: database connection factory and shared test fixtures"
```

---

### Task 6: Database Migration Script

**Files:**
- Create: `migrations/006_create_video_tables.sql`

- [ ] **Step 1: Write the migration**

```sql
-- migrations/006_create_video_tables.sql
-- NewsBrief video pipeline tables
-- Run against the 'cdb' database on RDS

CREATE TABLE IF NOT EXISTS video_runs (
    id              VARCHAR(32)  PRIMARY KEY,
    brief_id        INT          NOT NULL,
    issue_number    VARCHAR(16)  NOT NULL,
    run_date        DATE         NOT NULL,
    started_at      DATETIME(3)  NOT NULL,
    completed_at    DATETIME(3)  NULL,
    status          ENUM('running','completed','failed','partial') NOT NULL DEFAULT 'running',

    stage_extract_s     DECIMAL(8,2)  NULL,
    stage_script_s      DECIMAL(8,2)  NULL,
    stage_audio_s       DECIMAL(8,2)  NULL,
    stage_spec_s        DECIMAL(8,2)  NULL,
    stage_render_s      DECIMAL(8,2)  NULL,
    stage_post_s        DECIMAL(8,2)  NULL,
    stage_archive_s     DECIMAL(8,2)  NULL,
    total_duration_s    DECIMAL(8,2)  NULL,

    failed_stage    VARCHAR(32)   NULL,
    error_message   TEXT          NULL,

    stories_selected    JSON      NULL,
    word_count          INT       NULL,
    audio_duration_s    DECIMAL(8,2)  NULL,

    drive_folder_url    VARCHAR(512)  NULL,
    spec_path           VARCHAR(512)  NULL,

    elevenlabs_chars    INT       NULL,
    llm_input_tokens    INT       NULL,
    llm_output_tokens   INT       NULL,

    created_at      DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX idx_run_date (run_date),
    INDEX idx_brief_id (brief_id),
    FOREIGN KEY (brief_id) REFERENCES briefs(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS video_uploads (
    id              INT          AUTO_INCREMENT PRIMARY KEY,
    run_id          VARCHAR(32)  NOT NULL,
    platform        VARCHAR(32)  NOT NULL,
    status          ENUM('pending','uploading','completed','failed','skipped') NOT NULL DEFAULT 'pending',

    platform_id     VARCHAR(256)  NULL,
    platform_url    VARCHAR(512)  NULL,

    file_name       VARCHAR(256)  NOT NULL,
    file_size_bytes BIGINT        NULL,
    aspect_ratio    VARCHAR(8)    NOT NULL,
    content_type    VARCHAR(16)   NOT NULL,
    clip_id         VARCHAR(8)    NULL,

    started_at      DATETIME(3)  NULL,
    completed_at    DATETIME(3)  NULL,
    duration_s      DECIMAL(8,2) NULL,

    retry_count     INT          NOT NULL DEFAULT 0,
    error_message   TEXT         NULL,

    created_at      DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX idx_run_id (run_id),
    INDEX idx_platform (platform),
    INDEX idx_status (status),
    FOREIGN KEY (run_id) REFERENCES video_runs(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS video_scripts (
    id              INT          AUTO_INCREMENT PRIMARY KEY,
    run_id          VARCHAR(32)  NOT NULL UNIQUE,
    brief_id        INT          NOT NULL,

    hook_copy       TEXT         NOT NULL,
    lead_copy       TEXT         NOT NULL,
    scan_copy       TEXT         NOT NULL,
    why_copy        TEXT         NOT NULL,
    close_copy      TEXT         NOT NULL,

    lead_cluster_id     INT      NOT NULL,
    scan_cluster_ids    JSON     NOT NULL,
    selection_rationale TEXT     NULL,

    platform_meta       JSON    NULL,
    remotion_spec       JSON    NULL,

    created_at      DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX idx_run_id (run_id),
    FOREIGN KEY (run_id) REFERENCES video_runs(id),
    FOREIGN KEY (brief_id) REFERENCES briefs(id),
    FOREIGN KEY (lead_cluster_id) REFERENCES clusters(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS pronunciation_log (
    id              INT          AUTO_INCREMENT PRIMARY KEY,
    word            VARCHAR(128) NOT NULL,
    first_seen_date DATE         NOT NULL,
    first_seen_run  VARCHAR(32)  NOT NULL,
    cluster_id      INT          NULL,

    status          ENUM('pending_review','added_to_dict','ignored') NOT NULL DEFAULT 'pending_review',
    reviewed_at     DATETIME(3)  NULL,
    ssml_markup     TEXT         NULL,

    created_at      DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    UNIQUE INDEX idx_word (word),
    INDEX idx_status (status),
    FOREIGN KEY (first_seen_run) REFERENCES video_runs(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO schema_migrations (version, description, applied_at)
VALUES (6, 'Create video brief pipeline tables', NOW());
```

- [ ] **Step 2: Verify SQL syntax (dry run)**

Run: `cd /Users/arthurbillingsley/Downloads/Projects/NewsBrief && cat migrations/006_create_video_tables.sql | head -5`
Expected: First 5 lines of the migration file

- [ ] **Step 3: Commit**

```bash
git add migrations/006_create_video_tables.sql
git commit -m "feat: database migration for video pipeline tables"
```

**Note:** This migration is applied to the production RDS instance manually or via the CDB pipeline's existing migration runner. Do not auto-apply.

---

### Task 7: Stage 1 — EXTRACT

**Files:**
- Create: `src/stages/extract.py`
- Create: `tests/test_extract.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_extract.py
from datetime import date
from unittest.mock import MagicMock, patch

import pytest


def test_extract_returns_brief_and_clusters(sample_brief_data):
    from src.stages.extract import extract, ExtractResult

    mock_session = MagicMock()

    # Mock the Brief object
    mock_brief = MagicMock()
    mock_brief.id = sample_brief_data["brief_id"]
    mock_brief.issue_number = sample_brief_data["issue_number"]
    mock_brief.date = sample_brief_data["date"]

    # Mock clusters
    mock_clusters = []
    for c in sample_brief_data["clusters"]:
        mc = MagicMock()
        mc.id = c["id"]
        mc.headline = c["headline"]
        mc.body = c["body"]
        mc.why_this_matters = c["why_this_matters"]
        mc.what_changed = c["what_changed"]
        mc.status = c["status"]
        mc.confidence = c["confidence"]
        mc.position = c["position"]
        mc.sources = [MagicMock(source_name=s) for s in c["sources"]]
        mock_clusters.append(mc)

    mock_brief.clusters = mock_clusters

    # Mock query
    mock_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_brief

    result = extract(mock_session, run_date=date(2026, 6, 10))

    assert isinstance(result, ExtractResult)
    assert result.brief_id == 1
    assert result.issue_number == "N103"
    assert len(result.clusters) == 6


def test_extract_aborts_when_no_brief_found():
    from src.stages.extract import extract, ExtractError

    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

    with pytest.raises(ExtractError, match="No brief found"):
        extract(mock_session, run_date=date(2026, 6, 10))


def test_extract_aborts_on_stale_content():
    from src.stages.extract import extract, ExtractError

    mock_session = MagicMock()
    mock_brief = MagicMock()
    mock_brief.date = date(2026, 6, 9)  # yesterday's brief
    mock_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_brief

    with pytest.raises(ExtractError, match="stale content"):
        extract(mock_session, run_date=date(2026, 6, 10))


def test_extract_aborts_when_brief_has_no_clusters():
    from src.stages.extract import extract, ExtractError

    mock_session = MagicMock()
    mock_brief = MagicMock()
    mock_brief.date = date(2026, 6, 10)
    mock_brief.clusters = []
    mock_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_brief

    with pytest.raises(ExtractError, match="no stories"):
        extract(mock_session, run_date=date(2026, 6, 10))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_extract.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Write minimal implementation**

```python
# src/stages/extract.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List

import structlog
from sqlalchemy.orm import Session

from src.models import Brief

log = structlog.get_logger()


class ExtractError(Exception):
    pass


@dataclass
class ClusterData:
    id: int
    headline: str
    body: str
    why_this_matters: str
    what_changed: str | None
    status: str
    confidence: str
    position: int
    sources: List[str]


@dataclass
class ExtractResult:
    brief_id: int
    issue_number: str
    brief_date: date
    clusters: List[ClusterData]


def extract(session: Session, run_date: date) -> ExtractResult:
    log.info("extract.start", run_date=str(run_date))

    brief = (
        session.query(Brief)
        .filter(Brief.date <= run_date)
        .order_by(Brief.date.desc())
        .first()
    )

    if brief is None:
        raise ExtractError(f"No brief found for {run_date} or earlier.")

    if brief.date != run_date:
        raise ExtractError(
            f"Latest brief is {brief.date}, expected {run_date}. "
            "Not publishing stale content."
        )

    if not brief.clusters:
        raise ExtractError(
            f"Brief {brief.issue_number} ({brief.date}) has no stories."
        )

    clusters = [
        ClusterData(
            id=c.id,
            headline=c.headline,
            body=c.body,
            why_this_matters=c.why_this_matters or "",
            what_changed=c.what_changed,
            status=c.status or "NEW",
            confidence=c.confidence or "High",
            position=c.position,
            sources=[s.source_name for s in c.sources],
        )
        for c in sorted(brief.clusters, key=lambda x: x.position)
    ]

    log.info(
        "extract.done",
        brief_id=brief.id,
        issue=brief.issue_number,
        cluster_count=len(clusters),
    )

    return ExtractResult(
        brief_id=brief.id,
        issue_number=brief.issue_number,
        brief_date=brief.date,
        clusters=clusters,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_extract.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/stages/extract.py tests/test_extract.py
git commit -m "feat: Stage 1 EXTRACT — read clusters with stale-content guard"
```

---

### Task 8: Stage 2b — FORMAT (Number-to-Speech)

**Files:**
- Create: `src/stages/format_speech.py`
- Create: `tests/test_format_speech.py`

Building this before SCRIPT (Task 9) because SCRIPT's output feeds into FORMAT, and we want to test the formatter independently.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_format_speech.py
import pytest


def test_format_dollar_amount():
    from src.stages.format_speech import format_for_speech

    assert format_for_speech("Gas sits at $4.16 a gallon.") == "Gas sits at four sixteen a gallon."


def test_format_billion_dollar_amount():
    from src.stages.format_speech import format_for_speech

    assert format_for_speech("a $70 billion immigration bill") == "a seventy billion dollar immigration bill"


def test_format_large_billion():
    from src.stages.format_speech import format_for_speech

    assert format_for_speech("above $850 billion") == "above eight hundred fifty billion dollars"


def test_format_percentage():
    from src.stages.format_speech import format_for_speech

    assert format_for_speech("inflation hit 3.8 percent") == "inflation hit three point eight percent"


def test_format_vote_tally():
    from src.stages.format_speech import format_for_speech

    assert format_for_speech("a 214-212 vote") == "a two fourteen to two twelve vote"


def test_format_year():
    from src.stages.format_speech import format_for_speech

    # Years should be left as digits — ElevenLabs handles them well
    assert format_for_speech("funded through 2029") == "funded through 2029"


def test_format_plain_number():
    from src.stages.format_speech import format_for_speech

    assert format_for_speech("roughly 244,600 people killed") == "roughly two hundred forty four thousand six hundred people killed"


def test_format_leaves_non_numeric_text_unchanged():
    from src.stages.format_speech import format_for_speech

    text = "Iran shot down a U.S. Army Apache near the Strait of Hormuz."
    assert format_for_speech(text) == text


def test_format_one_fifth():
    from src.stages.format_speech import format_for_speech

    # Fractions like "a fifth" are already words — no change
    assert format_for_speech("carries one fifth of the world's oil") == "carries one fifth of the world's oil"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_format_speech.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Write minimal implementation**

```python
# src/stages/format_speech.py
from __future__ import annotations

import re


def _int_to_words(n: int) -> str:
    if n == 0:
        return "zero"

    ones = [
        "", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
        "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
        "seventeen", "eighteen", "nineteen",
    ]
    tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
    scales = [(1_000_000_000, "billion"), (1_000_000, "million"), (1_000, "thousand"), (100, "hundred")]

    if n < 0:
        return "negative " + _int_to_words(-n)

    parts = []
    for scale_val, scale_name in scales:
        if n >= scale_val:
            parts.append(_int_to_words(n // scale_val))
            parts.append(scale_name)
            n %= scale_val

    if n >= 20:
        parts.append(tens[n // 10])
        if n % 10:
            parts.append(ones[n % 10])
    elif n > 0:
        parts.append(ones[n])

    return " ".join(parts)


def _format_dollar_billions(match: re.Match) -> str:
    amount = int(match.group(1).replace(",", ""))
    unit = match.group(2).lower()
    return f"{_int_to_words(amount)} {unit} dollars"


def _format_dollar_amount(match: re.Match) -> str:
    amount_str = match.group(1).replace(",", "")
    if "." in amount_str:
        dollars, cents = amount_str.split(".")
        d = int(dollars)
        c = int(cents)
        if c == 0:
            return _int_to_words(d) + " dollars"
        return _int_to_words(d) + " " + _int_to_words(c)
    else:
        return _int_to_words(int(amount_str)) + " dollars"


def _format_vote_tally(match: re.Match) -> str:
    a = int(match.group(1))
    b = int(match.group(2))
    return f"{_int_to_words(a)} to {_int_to_words(b)}"


def _format_percentage(match: re.Match) -> str:
    num_str = match.group(1)
    if "." in num_str:
        whole, frac = num_str.split(".")
        return f"{_int_to_words(int(whole))} point {_int_to_words(int(frac))} percent"
    return f"{_int_to_words(int(num_str))} percent"


def _format_plain_number(match: re.Match) -> str:
    num_str = match.group(0).replace(",", "")
    n = int(num_str)
    # Don't convert years (1900-2099)
    if 1900 <= n <= 2099:
        return match.group(0)
    return _int_to_words(n)


def format_for_speech(text: str) -> str:
    # Order matters: most specific patterns first

    # $X billion/million/trillion
    text = re.sub(
        r"\$(\d[\d,]*)\s+(billion|million|trillion)",
        _format_dollar_billions,
        text,
        flags=re.IGNORECASE,
    )

    # $X.XX (dollar amounts)
    text = re.sub(r"\$([\d,]+(?:\.\d+)?)", _format_dollar_amount, text)

    # Vote tallies: 214-212
    text = re.sub(r"(\d{2,3})-(\d{2,3})\b", _format_vote_tally, text)

    # Percentages: 3.8 percent
    text = re.sub(r"([\d.]+)\s+percent", _format_percentage, text)

    # Remaining plain numbers (comma-separated ok)
    text = re.sub(r"\b\d[\d,]+\b", _format_plain_number, text)

    return text
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_format_speech.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add src/stages/format_speech.py tests/test_format_speech.py
git commit -m "feat: Stage 2b FORMAT — deterministic number-to-speech conversion"
```

---

### Task 9: Stage 2 — SCRIPT (LLM Script Generation)

**Files:**
- Create: `src/stages/script.py`
- Create: `tests/test_script.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_script.py
import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.stages.extract import ClusterData, ExtractResult


def _make_extract_result(sample_brief_data) -> ExtractResult:
    clusters = [
        ClusterData(
            id=c["id"],
            headline=c["headline"],
            body=c["body"],
            why_this_matters=c["why_this_matters"] or "",
            what_changed=c.get("what_changed"),
            status=c["status"],
            confidence=c["confidence"],
            position=c["position"],
            sources=c["sources"],
        )
        for c in sample_brief_data["clusters"]
    ]
    return ExtractResult(
        brief_id=sample_brief_data["brief_id"],
        issue_number=sample_brief_data["issue_number"],
        brief_date=sample_brief_data["date"],
        clusters=clusters,
    )


def test_generate_script_returns_script_result(sample_brief_data):
    from src.stages.script import generate_script, ScriptResult

    extract_result = _make_extract_result(sample_brief_data)

    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(
            text=json.dumps(
                {
                    "lead_cluster_id": 1,
                    "scan_cluster_ids": [3, 4, 5, 10],
                    "selection_rationale": "Lead with Hormuz (DEVELOPING, highest stakes).",
                    "hook": "An American helicopter is down near the Strait of Hormuz.",
                    "lead": "Iran shot down a U.S. Army Apache near the Strait of Hormuz.",
                    "scan_intro": "Four more, fast.",
                    "scan_items": [
                        "One. The House sent Trump a $70 billion immigration bill.",
                        "Two. Trump put a housing regulator atop the intelligence community.",
                        "Three. Gas sits at $4.16 a gallon.",
                        "Four. OpenAI filed to go public above $850 billion.",
                    ],
                    "why": "Here is the thread. The war near Hormuz is the same war showing up in your gas tank.",
                    "close": "That is the brief for June tenth. Every source shown. Every claim tagged. The full record is linked below. Decide.",
                    "platform_meta": {
                        "youtube_title": "COGNOSCERE Daily Brief - June 10, 2026",
                    },
                }
            )
        )
    ]
    mock_response.usage = MagicMock(input_tokens=4200, output_tokens=1800)

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    result = generate_script(extract_result, client=mock_client)

    assert isinstance(result, ScriptResult)
    assert result.lead_cluster_id == 1
    assert result.scan_cluster_ids == [3, 4, 5, 10]
    assert "Hormuz" in result.hook
    assert result.input_tokens == 4200
    assert result.output_tokens == 1800
    mock_client.messages.create.assert_called_once()


def test_generate_script_uses_correct_model(sample_brief_data):
    from src.stages.script import generate_script

    extract_result = _make_extract_result(sample_brief_data)

    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(
            text=json.dumps(
                {
                    "lead_cluster_id": 1,
                    "scan_cluster_ids": [3, 4, 5],
                    "selection_rationale": "test",
                    "hook": "hook",
                    "lead": "lead",
                    "scan_intro": "intro",
                    "scan_items": ["One. item1", "Two. item2", "Three. item3"],
                    "why": "why",
                    "close": "close",
                    "platform_meta": {},
                }
            )
        )
    ]
    mock_response.usage = MagicMock(input_tokens=100, output_tokens=100)

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    generate_script(extract_result, client=mock_client)

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-20250514"


def test_generate_script_raises_on_invalid_json(sample_brief_data):
    from src.stages.script import generate_script, ScriptError

    extract_result = _make_extract_result(sample_brief_data)

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="not valid json {{{")]
    mock_response.usage = MagicMock(input_tokens=100, output_tokens=100)

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with pytest.raises(ScriptError, match="Failed to parse"):
        generate_script(extract_result, client=mock_client)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_script.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Write minimal implementation**

```python
# src/stages/script.py
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import structlog

from src.stages.extract import ExtractResult

log = structlog.get_logger()

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096


class ScriptError(Exception):
    pass


@dataclass
class ScriptResult:
    lead_cluster_id: int
    scan_cluster_ids: List[int]
    selection_rationale: str
    hook: str
    lead: str
    scan_intro: str
    scan_items: List[str]
    why: str
    close: str
    platform_meta: Dict[str, Any]
    input_tokens: int
    output_tokens: int

    @property
    def full_scan(self) -> str:
        return self.scan_intro + "\n" + "\n".join(self.scan_items)

    @property
    def word_count(self) -> int:
        all_text = " ".join(
            [self.hook, self.lead, self.full_scan, self.why, self.close]
        )
        return len(all_text.split())


def _build_prompt(extract: ExtractResult) -> str:
    cluster_block = ""
    for c in extract.clusters:
        sources_str = ", ".join(c.sources) if c.sources else "Unknown"
        cluster_block += f"""
---
CLUSTER ID: {c.id}
POSITION: {c.position}
STATUS: {c.status}
CONFIDENCE: {c.confidence}
HEADLINE: {c.headline}
BODY: {c.body}
WHY THIS MATTERS: {c.why_this_matters}
WHAT CHANGED: {c.what_changed or 'N/A'}
SOURCES: {sources_str}
"""

    return f"""You are the scriptwriter for the COGNOSCERE Daily Video Brief, a 2-minute audio/visual news briefing.

Today's date: {extract.brief_date.strftime('%B %d, %Y')}
Issue: #{extract.issue_number}

Below are today's story clusters from the COGNOSCERE Daily Brief. Select stories and write a narration script.

CLUSTERS:
{cluster_block}

INSTRUCTIONS:
1. Select ONE lead story (prefer DEVELOPING status, highest stakes).
2. Select 3-4 SCAN stories (different domains, NEW preferred, broad impact).
3. Write the script in 5 slots. Target 290-310 words total. 2:00 is a ceiling, not a quota.

SLOT STRUCTURE:
- HOOK (0:00-0:10, ~25 words): Stop the scroll. Biggest stakes as consequence, not headline. No logo, no intro.
- LEAD (0:10-0:50, ~100 words): What happened. What changed. 2-3 key facts. One-line stakes.
- SCAN (0:50-1:30, ~100 words total): "{N} more, fast." Then numbered items. Each ~25 words, self-contained.
- WHY IT MATTERS (1:30-1:50, ~50 words): "Here is the thread." Tie the day together. Synthesis, not new facts.
- CLOSE (1:50-2:00, ~20 words): "That is the brief for [date]." Provenance stamp. End with "Decide."

CRITICAL RULES:
- Each SCAN item must be comprehensible in total isolation. No references to HOOK or LEAD.
- Use CANONICAL numeric values ($4.16, $70 billion, 214-212). Do NOT spell out numbers.
- Short declaratives. No hedging. No em dashes. Punchline first.
- Every fact must come from the cluster data above. Do not invent details.

Also generate platform_meta with these keys: youtube_title, youtube_description, youtube_tags, youtube_short_title, facebook_caption, facebook_reel_caption, instagram_caption, linkedin_caption.

All CTA links should use this exact URL (no UTM tags — those are added by the pipeline):
- Full record: https://www.cognoscerellc.com/news/{extract.brief_date.strftime('%Y-%m-%d')}/
- Subscribe: https://cognoscerellc.substack.com
- CIFaaS: https://cifaas.cognoscerellc.com

Return ONLY valid JSON with this exact structure:
{{
  "lead_cluster_id": <int>,
  "scan_cluster_ids": [<int>, ...],
  "selection_rationale": "<string>",
  "hook": "<string>",
  "lead": "<string>",
  "scan_intro": "<string>",
  "scan_items": ["<string>", ...],
  "why": "<string>",
  "close": "<string>",
  "platform_meta": {{...}}
}}"""


def generate_script(extract: ExtractResult, client: Any) -> ScriptResult:
    log.info("script.start", issue=extract.issue_number, cluster_count=len(extract.clusters))

    prompt = _build_prompt(extract)

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = response.content[0].text
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ScriptError(f"Failed to parse LLM response as JSON: {e}\nRaw: {raw_text[:500]}")

    required_keys = ["lead_cluster_id", "scan_cluster_ids", "hook", "lead", "scan_intro", "scan_items", "why", "close"]
    missing = [k for k in required_keys if k not in data]
    if missing:
        raise ScriptError(f"LLM response missing required keys: {missing}")

    result = ScriptResult(
        lead_cluster_id=data["lead_cluster_id"],
        scan_cluster_ids=data["scan_cluster_ids"],
        selection_rationale=data.get("selection_rationale", ""),
        hook=data["hook"],
        lead=data["lead"],
        scan_intro=data["scan_intro"],
        scan_items=data["scan_items"],
        why=data["why"],
        close=data["close"],
        platform_meta=data.get("platform_meta", {}),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )

    log.info(
        "script.done",
        lead_cluster=result.lead_cluster_id,
        scan_clusters=result.scan_cluster_ids,
        word_count=result.word_count,
        tokens_in=input_tokens,
        tokens_out=output_tokens,
    )

    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_script.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/stages/script.py tests/test_script.py
git commit -m "feat: Stage 2 SCRIPT — LLM narration generation with slot structure"
```

---

### Task 10: Orchestrator Skeleton

**Files:**
- Create: `src/run.py`
- Create: `tests/test_run.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_run.py
import argparse
from datetime import date
from unittest.mock import MagicMock, patch

import pytest


def test_parse_args_defaults():
    from src.run import parse_args

    args = parse_args([])
    assert args.date is None
    assert args.preview is False
    assert args.dry_run is False
    assert args.force is False
    assert args.stage is None


def test_parse_args_with_date():
    from src.run import parse_args

    args = parse_args(["--date", "2026-06-10"])
    assert args.date == "2026-06-10"


def test_parse_args_with_flags():
    from src.run import parse_args

    args = parse_args(["--preview", "--force"])
    assert args.preview is True
    assert args.force is True


def test_resolve_run_date_uses_today_when_no_arg():
    from src.run import resolve_run_date

    result = resolve_run_date(None)
    assert result == date.today()


def test_resolve_run_date_parses_arg():
    from src.run import resolve_run_date

    result = resolve_run_date("2026-06-10")
    assert result == date(2026, 6, 10)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_run.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Write minimal implementation**

```python
# src/run.py
from __future__ import annotations

import argparse
import sys
import time
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

import structlog

from src.config import load_config
from src.lib.db import get_engine, get_session
from src.models import VideoRun
from src.stages.extract import extract, ExtractError
from src.stages.format_speech import format_for_speech
from src.stages.script import generate_script, ScriptError

log = structlog.get_logger()


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="COGNOSCERE NewsBrief Pipeline")
    parser.add_argument("--date", type=str, help="Run date (YYYY-MM-DD). Defaults to today.")
    parser.add_argument("--preview", action="store_true", help="Generate artifacts but do not upload.")
    parser.add_argument("--dry-run", action="store_true", help="Generate script only. No audio or video.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing run for this date.")
    parser.add_argument("--stage", type=str, help="Re-run a single stage (extract|script|audio|render|post|archive).")
    parser.add_argument("--approve", action="store_true", help="Approve a gated run for publishing.")
    parser.add_argument("--kill", action="store_true", help="Kill a gated run to prevent publishing.")
    parser.add_argument("--platform", type=str, help="Re-upload to a specific platform only.")
    return parser.parse_args(argv)


def resolve_run_date(date_str: Optional[str]) -> date:
    if date_str is None:
        return date.today()
    return date.fromisoformat(date_str)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    run_date = resolve_run_date(args.date)
    run_id = f"vr-{run_date.isoformat()}"

    log.info("pipeline.start", run_id=run_id, run_date=str(run_date), preview=args.preview, dry_run=args.dry_run)

    config = load_config()
    engine = get_engine(config)
    session = get_session(engine)

    # Create run record
    started_at = datetime.utcnow()
    run = VideoRun(
        id=run_id,
        brief_id=0,  # updated after extract
        issue_number="",
        run_date=run_date,
        started_at=started_at,
        status="running",
    )

    try:
        # Stage 1: EXTRACT
        t0 = time.monotonic()
        extract_result = extract(session, run_date)
        run.brief_id = extract_result.brief_id
        run.issue_number = extract_result.issue_number
        run.stage_extract_s = Decimal(str(round(time.monotonic() - t0, 2)))

        log.info("pipeline.extract.done", brief_id=extract_result.brief_id, clusters=len(extract_result.clusters))

        # Stage 2: SCRIPT
        import anthropic

        t0 = time.monotonic()
        client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        script_result = generate_script(extract_result, client=client)
        run.stage_script_s = Decimal(str(round(time.monotonic() - t0, 2)))
        run.stories_selected = [script_result.lead_cluster_id] + script_result.scan_cluster_ids
        run.word_count = script_result.word_count
        run.llm_input_tokens = script_result.input_tokens
        run.llm_output_tokens = script_result.output_tokens

        log.info("pipeline.script.done", word_count=script_result.word_count)

        # Stage 2b: FORMAT
        formatted_hook = format_for_speech(script_result.hook)
        formatted_lead = format_for_speech(script_result.lead)
        formatted_scan_items = [format_for_speech(item) for item in script_result.scan_items]
        formatted_scan_intro = format_for_speech(script_result.scan_intro)
        formatted_why = format_for_speech(script_result.why)
        formatted_close = format_for_speech(script_result.close)

        log.info("pipeline.format.done")

        if args.dry_run:
            log.info("pipeline.dry_run.complete")
            print(f"\n--- HOOK ---\n{formatted_hook}")
            print(f"\n--- LEAD ---\n{formatted_lead}")
            print(f"\n--- SCAN ---\n{formatted_scan_intro}")
            for item in formatted_scan_items:
                print(f"  {item}")
            print(f"\n--- WHY IT MATTERS ---\n{formatted_why}")
            print(f"\n--- CLOSE ---\n{formatted_close}")
            print(f"\nWord count: {script_result.word_count}")
            run.status = "completed"
            return

        # Stages 3-8 are implemented in Plans B, C, D
        log.info("pipeline.plan_a_complete", message="Stages 3-8 not yet implemented. Use --dry-run for script output.")
        run.status = "completed"

    except (ExtractError, ScriptError) as e:
        log.error("pipeline.failed", error=str(e))
        run.status = "failed"
        run.error_message = str(e)
        raise

    finally:
        run.completed_at = datetime.utcnow()
        if run.started_at and run.completed_at:
            run.total_duration_s = Decimal(
                str(round((run.completed_at - run.started_at).total_seconds(), 2))
            )
        session.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_run.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/run.py tests/test_run.py
git commit -m "feat: orchestrator skeleton with CLI args, stages 1-2b wired up"
```

---

### Task 11: Pronunciation YAML Placeholder

**Files:**
- Create: `config/pronunciation.yaml`

This is needed by Plan B but we create the file now so the project structure is complete.

- [ ] **Step 1: Create the pronunciation dictionary**

```yaml
# config/pronunciation.yaml
# SSML pronunciation dictionary for ElevenLabs TTS
# Format: word -> SSML phoneme or say-as replacement
# Managed by the pipeline; new words flagged in pronunciation_log table

proper_nouns:
  Hormuz: '<phoneme alphabet="ipa" ph="hɔːɹˈmuːz">Hormuz</phoneme>'
  Netanyahu: '<phoneme alphabet="ipa" ph="nɛtɑnˈjɑːhuː">Netanyahu</phoneme>'
  Pulte: '<phoneme alphabet="ipa" ph="ˈpʌltiː">Pulte</phoneme>'
  Shahed: '<phoneme alphabet="ipa" ph="ʃɑːˈhɛd">Shahed</phoneme>'
  CENTCOM: '<phoneme alphabet="ipa" ph="ˈsɛntkɒm">CENTCOM</phoneme>'
  Uppsala: '<phoneme alphabet="ipa" ph="ˈʊpsɑːlɑː">Uppsala</phoneme>'
  COGNOSCERE: '<phoneme alphabet="ipa" ph="kɒɡˈnɒʃɛɹeɪ">COGNOSCERE</phoneme>'
  CIFaaS: '<say-as interpret-as="characters">CIF</say-as>aas'

acronyms:
  speak_as_word:
    - NATO
    - FEMA
    - CENTCOM
  spell_out:
    - ICE
    - SEC
    - IPO
    - NSO
    - FBI
    - CIA
```

- [ ] **Step 2: Commit**

```bash
git add config/pronunciation.yaml
git commit -m "feat: initial SSML pronunciation dictionary"
```

---

### Task 12: End-to-End Dry Run Test

**Files:**
- No new files. Integration test using existing code.

- [ ] **Step 1: Run the full test suite**

Run: `.venv/bin/pytest tests/ -v`
Expected: All tests pass (approximately 27 tests)

- [ ] **Step 2: Verify dry-run script output manually**

This requires a live Anthropic API key. If available:

```bash
cd /Users/arthurbillingsley/Downloads/Projects/NewsBrief
cp .env.example .env
# Edit .env with real DB credentials and ANTHROPIC_API_KEY
source .venv/bin/activate
python -m src.run --date 2026-06-10 --dry-run
```

Expected output: A formatted 5-slot script with ~300 words, all numbers in spoken form.

If no API key available, verify with mocked test:

Run: `.venv/bin/pytest tests/test_script.py tests/test_format_speech.py -v`
Expected: All pass

- [ ] **Step 3: Final commit with any fixes**

```bash
git add -A
git status  # verify nothing unexpected
git commit -m "chore: Plan A complete — core pipeline foundation with stages 1-2b"
```

---

## Plan A Completion Checklist

After all tasks are done, verify:

- [ ] `src/config.py` loads all env vars with validation
- [ ] `src/lib/retry.py` provides exponential backoff with jitter
- [ ] `src/lib/db.py` connects to MySQL via SQLAlchemy
- [ ] `src/models.py` defines ORM for all 8 tables (4 existing read-only + 4 new)
- [ ] `migrations/006_create_video_tables.sql` creates video pipeline tables
- [ ] `src/stages/extract.py` reads clusters with stale-content guard (R6)
- [ ] `src/stages/format_speech.py` converts canonical numbers to spoken forms (R2)
- [ ] `src/stages/script.py` generates 5-slot narration via Claude Sonnet (R10)
- [ ] `src/run.py` orchestrates stages 1-2b with CLI args
- [ ] `config/pronunciation.yaml` has initial SSML dictionary
- [ ] All tests pass
- [ ] `--dry-run` produces a readable script

**Next:** Plan B (Audio + Spec) builds on these data structures to generate audio and the Remotion JSON spec.
