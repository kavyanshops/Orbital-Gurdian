"""
MongoDB Database Connection and Operations
Collision Avoidance System - Analysis History Storage
"""

import os
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pymongo import MongoClient, DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database
from bson import ObjectId


# Configuration
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
DATABASE_NAME = os.getenv('MONGO_DB_NAME', 'collision_avoidance')

# Global connection
_client: Optional[MongoClient] = None
_db: Optional[Database] = None


def get_database() -> Database:
    """Get or create MongoDB connection."""
    global _client, _db
    
    if _db is None:
        _client = MongoClient(MONGO_URI)
        _db = _client[DATABASE_NAME]
        
        # Create indexes for better query performance
        _db.analyses.create_index([('created_at', DESCENDING)])
        _db.analyses.create_index('satellite_name')
        _db.analyses.create_index('overall_status')
        
    return _db


def get_analyses_collection() -> Collection:
    """Get the analyses collection."""
    return get_database().analyses


def save_analysis(analysis_data: Dict[str, Any]) -> str:
    """
    Save an analysis result to the database.
    
    Args:
        analysis_data: The complete analysis result from conjunction screening
        
    Returns:
        The inserted document ID as string
    """
    collection = get_analyses_collection()
    
    # Add metadata
    document = {
        **analysis_data,
        'created_at': datetime.now(timezone.utc),
        'version': '1.0'
    }
    
    result = collection.insert_one(document)
    return str(result.inserted_id)


def get_analysis_by_id(analysis_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a specific analysis by ID.
    
    Args:
        analysis_id: MongoDB document ID
        
    Returns:
        The analysis document or None if not found
    """
    try:
        collection = get_analyses_collection()
        document = collection.find_one({'_id': ObjectId(analysis_id)})
        
        if document:
            document['_id'] = str(document['_id'])
            return document
        return None
    except Exception:
        return None


def get_analysis_history(
    limit: int = 50,
    skip: int = 0,
    status_filter: Optional[str] = None,
    satellite_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get analysis history with optional filters.
    
    Args:
        limit: Maximum number of results
        skip: Number of results to skip (for pagination)
        status_filter: Filter by overall_status ('SAFE' or 'WARNINGS_PRESENT')
        satellite_filter: Filter by satellite name (case-insensitive substring)
        
    Returns:
        List of analysis documents
    """
    collection = get_analyses_collection()
    
    # Build query
    query: Dict[str, Any] = {}
    if status_filter:
        query['overall_status'] = status_filter
    if satellite_filter:
        query['satellite_name'] = {'$regex': satellite_filter, '$options': 'i'}
    
    # Execute query
    cursor = collection.find(
        query,
        {
            'satellite_name': 1,
            'overall_status': 1,
            'warnings_count': 1,
            'debris_analyzed': 1,
            'created_at': 1,
            'analysis_start': 1,
            'analysis_end': 1
        }
    ).sort('created_at', DESCENDING).skip(skip).limit(limit)
    
    results = []
    for doc in cursor:
        doc['_id'] = str(doc['_id'])
        results.append(doc)
    
    return results


def get_analysis_count(
    status_filter: Optional[str] = None,
    satellite_filter: Optional[str] = None
) -> int:
    """Get total count of analyses matching filters."""
    collection = get_analyses_collection()
    
    query: Dict[str, Any] = {}
    if status_filter:
        query['overall_status'] = status_filter
    if satellite_filter:
        query['satellite_name'] = {'$regex': satellite_filter, '$options': 'i'}
    
    return collection.count_documents(query)


def delete_analysis(analysis_id: str) -> bool:
    """Delete an analysis by ID."""
    try:
        collection = get_analyses_collection()
        result = collection.delete_one({'_id': ObjectId(analysis_id)})
        return result.deleted_count > 0
    except Exception:
        return False


def get_statistics() -> Dict[str, Any]:
    """Get overall system statistics."""
    collection = get_analyses_collection()
    
    total = collection.count_documents({})
    warnings = collection.count_documents({'overall_status': 'WARNINGS_PRESENT'})
    safe = collection.count_documents({'overall_status': 'SAFE'})
    
    # Get most analyzed satellites
    pipeline = [
        {'$group': {'_id': '$satellite_name', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}},
        {'$limit': 5}
    ]
    top_satellites = list(collection.aggregate(pipeline))
    
    return {
        'total_analyses': total,
        'warnings_detected': warnings,
        'safe_analyses': safe,
        'warning_rate': (warnings / total * 100) if total > 0 else 0,
        'top_satellites': [{'name': s['_id'], 'count': s['count']} for s in top_satellites]
    }


def close_connection():
    """Close the MongoDB connection."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
