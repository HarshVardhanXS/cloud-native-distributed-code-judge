from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models import Base, User, Problem, Submission, TestCase
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./judge.db")

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

SEED_PROBLEMS = [
    # 10 coding problems
    {
        "title": "Two Sum",
        "description": "Given an array of integers and a target, return indices of the two numbers that add up to target.",
        "difficulty": "Easy",
        "tags": ["Array", "Hash Table"],
    },
    {
        "title": "Valid Parentheses",
        "description": "Determine if the input string of brackets is valid.",
        "difficulty": "Easy",
        "tags": ["Stack", "String"],
    },
    {
        "title": "Merge Two Sorted Lists",
        "description": "Merge two sorted linked lists and return the merged list.",
        "difficulty": "Easy",
        "tags": ["Linked List", "Recursion"],
    },
    {
        "title": "Maximum Subarray",
        "description": "Find the contiguous subarray with the largest sum and return its sum.",
        "difficulty": "Medium",
        "tags": ["Array", "Dynamic Programming"],
    },
    {
        "title": "Product of Array Except Self",
        "description": "Return an array where each element is the product of all other elements.",
        "difficulty": "Medium",
        "tags": ["Array", "Prefix Sum"],
    },
    {
        "title": "Group Anagrams",
        "description": "Group strings that are anagrams of each other.",
        "difficulty": "Medium",
        "tags": ["Hash Table", "String", "Sorting"],
    },
    {
        "title": "Top K Frequent Elements",
        "description": "Return the k most frequent elements in an array.",
        "difficulty": "Medium",
        "tags": ["Heap", "Hash Table", "Bucket Sort"],
    },
    {
        "title": "Number of Islands",
        "description": "Count the number of islands in a 2D grid.",
        "difficulty": "Medium",
        "tags": ["DFS", "BFS", "Matrix"],
    },
    {
        "title": "Median of Two Sorted Arrays",
        "description": "Find the median of two sorted arrays in logarithmic time.",
        "difficulty": "Hard",
        "tags": ["Binary Search", "Array"],
    },
    {
        "title": "Trapping Rain Water",
        "description": "Compute how much water can be trapped after raining.",
        "difficulty": "Hard",
        "tags": ["Two Pointers", "Array", "Stack"],
    },
    # 5 algorithmic challenges
    {
        "title": "Longest Increasing Subsequence",
        "description": "Return the length of the longest strictly increasing subsequence.",
        "difficulty": "Medium",
        "tags": ["Dynamic Programming", "Binary Search"],
    },
    {
        "title": "Dijkstra Shortest Path",
        "description": "Compute shortest path distances from a source in a weighted graph with non-negative weights.",
        "difficulty": "Medium",
        "tags": ["Graph", "Shortest Path", "Heap"],
    },
    {
        "title": "Kruskal Minimum Spanning Tree",
        "description": "Find the total weight of the minimum spanning tree of an undirected weighted graph.",
        "difficulty": "Hard",
        "tags": ["Graph", "Union Find", "Greedy"],
    },
    {
        "title": "Knapsack 0/1",
        "description": "Maximize value in a knapsack with weight constraints where each item can be picked once.",
        "difficulty": "Medium",
        "tags": ["Dynamic Programming"],
    },
    {
        "title": "N-Queens",
        "description": "Place n queens on an n x n chessboard so no two queens attack each other.",
        "difficulty": "Hard",
        "tags": ["Backtracking", "Recursion"],
    },
    # 5 system design questions
    {
        "title": "Design URL Shortener",
        "description": "Design a scalable URL shortening service similar to bit.ly.",
        "difficulty": "Medium",
        "tags": ["System Design", "Scalability", "Databases"],
    },
    {
        "title": "Design Rate Limiter",
        "description": "Design a distributed rate limiter for APIs with strict and burst limits.",
        "difficulty": "Hard",
        "tags": ["System Design", "Distributed Systems"],
    },
    {
        "title": "Design Real-Time Chat Service",
        "description": "Design a real-time chat system supporting private and group messaging.",
        "difficulty": "Medium",
        "tags": ["System Design", "Realtime", "WebSocket"],
    },
    {
        "title": "Design Distributed Cache",
        "description": "Design a distributed caching layer with eviction policies and high availability.",
        "difficulty": "Hard",
        "tags": ["System Design", "Caching", "Consistency"],
    },
    {
        "title": "Design Notification System",
        "description": "Design a high-throughput notification system for email, SMS, and push channels.",
        "difficulty": "Medium",
        "tags": ["System Design", "Messaging", "Queues"],
    },
]


def seed_problems() -> None:
    """Seed at least 20 problems if they do not already exist."""
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


def init_db():
    """Initialize all database tables"""
    Base.metadata.create_all(bind=engine)
    seed_problems()


def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
