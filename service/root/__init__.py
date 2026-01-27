# service/root/__init__.py
"""
词根服务模块 - 使用ORM
"""
import json
from flask import request, jsonify
from app.app import db
from model.root_model import Root
from utils import try_json_parse


def add():
    """增加词根"""
    data = request.get_json()
    name = data.get('name')
    meaning = data.get('meaning')
    similar = data.get('similar')
    cases = data.get('cases')
    
    try:
        similar_str = ','.join(similar) if isinstance(similar, list) else similar
        cases_str = json.dumps(cases, ensure_ascii=False) if cases else None
        
        root_data = {
            'name': name,
            'meaning': meaning,
            'similar': similar_str,
            'cases': cases_str,
        }
        Root.insert(root_data)
        
        return jsonify({
            'code': 200,
            'msg': 'success',
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 500,
            'msg': str(e),
        })


def delete():
    """删除词根"""
    data = request.get_json()
    root_id = data.get('id')
    
    try:
        Root.delete(root_id)
        return jsonify({
            'code': 200,
            'msg': 'success',
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 500,
            'msg': str(e),
        })


def update():
    """更新词根"""
    data = request.get_json()
    name = data.get('name')
    meaning = data.get('meaning')
    similar = data.get('similar')
    cases = data.get('cases')
    root_id = data.get('id')
    
    try:
        similar_str = ','.join(similar) if isinstance(similar, list) else similar
        cases_str = json.dumps(cases, ensure_ascii=False) if cases else None
        
        root_data = {
            'id': root_id,
            'name': name,
            'meaning': meaning,
            'similar': similar_str,
            'cases': cases_str,
        }
        Root.update(root_data)
        
        return jsonify({
            'code': 200,
            'msg': 'success',
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 500,
            'msg': str(e),
        })


def list_roots():
    """查询词根列表"""
    try:
        roots = Root.select_by()
        
        data_list = []
        for item in roots:
            data_list.append({
                'id': item.id,
                'name': item.name,
                'meaning': item.meaning,
                'similar': item.similar.split(',') if item.similar else [],
                'cases': try_json_parse(item.cases),
            })
        
        return jsonify({
            'code': 200,
            'data': {
                'data': data_list,
                'total': len(data_list),
                'page': 1,
            },
            'msg': 'success',
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'msg': str(e),
        })
