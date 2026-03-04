import logging

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from config import DATABASE_URL
from models import Base, Problem

logger = logging.getLogger(__name__)

SessionLocal = sessionmaker(autocommit=False, autoflush=False)
_engine = None
_db_ready = False


def _build_seed_problems() -> list[dict[str, object]]:
    coding_topics = [
        "Arrays", "Strings", "Hashing", "Prefix Sums", "Sliding Window",
        "Two Pointers", "Stacks", "Queues", "Linked Lists", "Binary Search",
        "Greedy", "Dynamic Programming", "Recursion", "Backtracking", "Trees",
        "Binary Trees", "Graphs", "Shortest Path", "Topological Sort", "Heaps",
        "Tries", "Bit Manipulation", "Math", "Union Find", "Intervals",
    ]
    coding_problems: list[dict[str, object]] = []
    for idx in range(1, 101):
        topic = coding_topics[(idx - 1) % len(coding_topics)]
        difficulty = "Easy" if idx % 5 in (1, 2) else ("Medium" if idx % 5 in (3, 4) else "Hard")
        coding_problems.append(
            {
                "title": f"Coding Challenge {idx}: {topic} Mastery",
                "description": (
                    f"You are given a real-world {topic.lower()} scenario that requires designing a robust algorithm. "
                    "Write a function named `solution` that handles edge cases, large input sizes, and deterministic output. "
                    "Your implementation should include clear reasoning about complexity and correctness. "
                    "Provide output in exact format and optimize for interview-level constraints."
                ),
                "difficulty": difficulty,
                "tags": [topic, "Coding", "Interview Prep"],
            }
        )

    system_design_titles = [
        "Design LeetCode Platform",
        "Design URL Shortener",
        "Design Rate Limiter",
        "Design Real-Time Chat Service",
        "Design Distributed Cache",
        "Design Notification System",
        "Design Video Streaming Platform",
        "Design Online Judge for Competitions",
        "Design Food Delivery Platform",
        "Design Ride Sharing Platform",
        "Design Search Autocomplete",
        "Design API Gateway",
        "Design Metrics & Monitoring System",
        "Design News Feed",
        "Design Cloud File Storage",
        "Design Feature Flag Service",
        "Design Multi-Region Payments Router",
        "Design IoT Telemetry Pipeline",
        "Design Ads Auction Service",
        "Design Collaborative Whiteboard",
    ]
    system_design_problems: list[dict[str, object]] = []
    for title in system_design_titles:
        system_design_problems.append(
            {
                "title": title,
                "description": (
                    "Understanding the Problem:\n"
                    "1) Define functional requirements and explicitly call out out-of-scope items.\n"
                    "2) Define non-functional requirements including scalability, availability, latency, and security.\n"
                    "3) Propose core entities and API contracts.\n"
                    "4) Design a high-level architecture, data flow, and component responsibilities.\n"
                    "5) Discuss deep dives: scaling strategy, caching, queueing, failure handling, and observability.\n"
                    "6) Provide final trade-off summary and why the chosen design is appropriate."
                ),
                "difficulty": "Hard",
                "tags": ["System Design", "Architecture", "Scalability"],
            }
        )

    return coding_problems + system_design_problems


SEED_PROBLEMS = _build_seed_problems()


def seed_problems() -> None:
    """Seed at least 120 problems if they do not already exist."""
    get_engine()
    db = SessionLocal()
    try:
        existing_titles = {row[0] for row in db.query(Problem.title).all()}
        to_insert = [
            Problem(
                title=item["title"],
                description=item["description"],
                difficulty=item["difficulty"],
                tags=item.get("tags"),
            )
            for item in SEED_PROBLEMS
            if item["title"] not in existing_titles
        ]
        if to_insert:
            db.add_all(to_insert)
            db.commit()
    finally:
        db.close()


def get_engine():
    """Create SQLAlchemy engine lazily and bind sessionmaker once."""
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        SessionLocal.configure(bind=_engine)
    return _engine


def is_db_ready() -> bool:
    """Return last known database initialization state."""
    return _db_ready


def init_db() -> bool:
    """Initialize database tables during explicit startup only."""
    global _db_ready
    try:
        Base.metadata.create_all(bind=get_engine())
        seed_problems()
        _db_ready = True
        return True
    except SQLAlchemyError as exc:
        _db_ready = False
        logger.warning("Database initialization failed: %s", exc)
        return False
    except Exception as exc:
        _db_ready = False
        logger.exception("Unexpected database initialization failure: %s", exc)
        return False


def get_db() -> Session:
    """Get database session"""
    get_engine()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
