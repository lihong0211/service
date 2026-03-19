#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
开发入口：Uvicorn 跑 FastAPI，带热重载
"""
import os
import sys

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 3000))
    uvicorn.run(
        "app.app:app",
        host="0.0.0.0",
        port=port,
        reload=True,
    )
