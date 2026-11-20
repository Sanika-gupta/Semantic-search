#!/usr/bin/env python3
"""
Run the FastAPI server for semantic search.
"""

import uvicorn
import argparse


def main():
    parser = argparse.ArgumentParser(description='Run VLA Research Engine API')
    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='Port to bind to (default: 8000)'
    )
    parser.add_argument(
        '--reload',
        action='store_true',
        help='Enable auto-reload for development'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("VLA Research Engine API Server")
    print("=" * 60)
    print(f"Starting server at http://{args.host}:{args.port}")
    print(f"API docs available at http://{args.host}:{args.port}/docs")
    print("=" * 60)

    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )


if __name__ == '__main__':
    main()
