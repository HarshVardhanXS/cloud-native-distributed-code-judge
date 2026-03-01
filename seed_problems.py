from datetime import datetime

from database import SessionLocal
from models import Problem


def build_problems() -> list[dict]:
    return [
        {
            "title": "Two Sum",
            "description": "Given an array of integers and a target, return indices of the two numbers that add up to target.",
            "difficulty": "Easy",
            "tags": ["Array", "Hash Table"],
            "created_at": datetime.utcnow(),
        },
        {
            "title": "Valid Parentheses",
            "description": "Determine if an input string containing brackets is valid.",
            "difficulty": "Easy",
            "tags": ["Stack", "String"],
            "created_at": datetime.utcnow(),
        },
        {
            "title": "Merge Two Sorted Lists",
            "description": "Merge two sorted linked lists and return the merged sorted list.",
            "difficulty": "Easy",
            "tags": ["Linked List", "Recursion"],
            "created_at": datetime.utcnow(),
        },
        {
            "title": "Best Time to Buy and Sell Stock",
            "description": "Find the maximum profit from a single buy and sell operation.",
            "difficulty": "Easy",
            "tags": ["Array", "Dynamic Programming"],
            "created_at": datetime.utcnow(),
        },
        {
            "title": "Longest Common Prefix",
            "description": "Find the longest common prefix string among an array of strings.",
            "difficulty": "Easy",
            "tags": ["String", "Trie"],
            "created_at": datetime.utcnow(),
        },
        {
            "title": "3Sum",
            "description": "Find all unique triplets in the array that sum to zero.",
            "difficulty": "Medium",
            "tags": ["Array", "Two Pointers", "Sorting"],
            "created_at": datetime.utcnow(),
        },
        {
            "title": "Group Anagrams",
            "description": "Group strings that are anagrams of each other.",
            "difficulty": "Medium",
            "tags": ["Hash Table", "String", "Sorting"],
            "created_at": datetime.utcnow(),
        },
        {
            "title": "Top K Frequent Elements",
            "description": "Return the k most frequent elements from an integer array.",
            "difficulty": "Medium",
            "tags": ["Heap", "Hash Table", "Bucket Sort"],
            "created_at": datetime.utcnow(),
        },
        {
            "title": "Number of Islands",
            "description": "Count the number of islands in a 2D grid map.",
            "difficulty": "Medium",
            "tags": ["DFS", "BFS", "Matrix"],
            "created_at": datetime.utcnow(),
        },
        {
            "title": "Longest Increasing Subsequence",
            "description": "Return the length of the longest strictly increasing subsequence.",
            "difficulty": "Medium",
            "tags": ["Dynamic Programming", "Binary Search"],
            "created_at": datetime.utcnow(),
        },
        {
            "title": "Coin Change",
            "description": "Find the fewest number of coins required to make up a given amount.",
            "difficulty": "Medium",
            "tags": ["Dynamic Programming", "Breadth-First Search"],
            "created_at": datetime.utcnow(),
        },
        {
            "title": "Kth Largest Element in an Array",
            "description": "Find the kth largest element in an unsorted array.",
            "difficulty": "Medium",
            "tags": ["Heap", "Quickselect"],
            "created_at": datetime.utcnow(),
        },
        {
            "title": "Word Ladder",
            "description": "Find the shortest transformation sequence from begin word to end word.",
            "difficulty": "Hard",
            "tags": ["BFS", "Hash Table", "String"],
            "created_at": datetime.utcnow(),
        },
        {
            "title": "Trapping Rain Water",
            "description": "Compute how much water can be trapped after raining.",
            "difficulty": "Hard",
            "tags": ["Array", "Two Pointers", "Stack"],
            "created_at": datetime.utcnow(),
        },
        {
            "title": "Median of Two Sorted Arrays",
            "description": "Find the median of two sorted arrays in O(log(m+n)) time.",
            "difficulty": "Hard",
            "tags": ["Array", "Binary Search", "Divide and Conquer"],
            "created_at": datetime.utcnow(),
        },
        {
            "title": "N-Queens",
            "description": "Place n queens on an n x n board so no two queens attack each other.",
            "difficulty": "Hard",
            "tags": ["Backtracking", "Recursion"],
            "created_at": datetime.utcnow(),
        },
        {
            "title": "Design URL Shortener",
            "description": "Design a scalable URL shortener similar to bit.ly with analytics.",
            "difficulty": "Medium",
            "tags": ["System Design", "Scalability", "Databases"],
            "created_at": datetime.utcnow(),
        },
        {
            "title": "Design Rate Limiter",
            "description": "Design a distributed rate limiter that supports burst and steady-state limits.",
            "difficulty": "Hard",
            "tags": ["System Design", "Distributed Systems", "Caching"],
            "created_at": datetime.utcnow(),
        },
        {
            "title": "Design Real-Time Chat Service",
            "description": "Design a low-latency chat service supporting private and group conversations.",
            "difficulty": "Medium",
            "tags": ["System Design", "WebSocket", "Messaging"],
            "created_at": datetime.utcnow(),
        },
        {
            "title": "Design Distributed Cache",
            "description": "Design a distributed cache with replication, eviction policy, and consistency options.",
            "difficulty": "Hard",
            "tags": ["System Design", "Caching", "Consistency"],
            "created_at": datetime.utcnow(),
        },
        {
            "title": "Design Notification Service",
            "description": "Design a notification platform for email, SMS, and push at large scale.",
            "difficulty": "Medium",
            "tags": ["System Design", "Queues", "Reliability"],
            "created_at": datetime.utcnow(),
        },
        {
            "title": "Design Search Autocomplete",
            "description": "Design an autocomplete service with ranking, freshness, and typo tolerance.",
            "difficulty": "Hard",
            "tags": ["System Design", "Search", "Trie"],
            "created_at": datetime.utcnow(),
        },
    ]


def seed_problems() -> None:
    session = SessionLocal()
    try:
        payload = build_problems()
        existing_titles = {row[0] for row in session.query(Problem.title).all()}

        problem_rows = [
            Problem(
                title=item["title"],
                description=item["description"],
                difficulty=item["difficulty"],
                tags=item.get("tags"),
                created_at=item["created_at"],
            )
            for item in payload
            if item["title"] not in existing_titles
        ]

        session.add_all(problem_rows)
        session.commit()

        print(f"20+ problems seeded successfully. Inserted: {len(problem_rows)}")
    finally:
        session.close()


if __name__ == "__main__":
    seed_problems()