# service/affix/__init__.py
"""
词缀服务模块 - 使用ORM
"""
import json
from flask import request, jsonify
from app.app import db
from model.affix_model import Affix
from utils import try_json_parse


def add():
    """增加词缀"""
    data = request.get_json()
    name = data.get('name')
    meaning = data.get('meaning')
    similar = data.get('similar')
    cases = data.get('cases')
    
    try:
        similar_str = ','.join(similar) if isinstance(similar, list) else similar
        cases_str = json.dumps(cases, ensure_ascii=False) if cases else None
        
        affix_data = {
            'name': name,
            'meaning': meaning,
            'similar': similar_str,
            'cases': cases_str,
        }
        Affix.insert(affix_data)
        
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
    """删除词缀"""
    data = request.get_json()
    affix_id = data.get('id')
    
    try:
        Affix.delete(affix_id)
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
    """更新词缀"""
    data = request.get_json()
    name = data.get('name')
    meaning = data.get('meaning')
    similar = data.get('similar')
    cases = data.get('cases')
    affix_id = data.get('id')
    
    try:
        similar_str = ','.join(similar) if isinstance(similar, list) else similar
        cases_str = json.dumps(cases, ensure_ascii=False) if cases else None
        
        affix_data = {
            'id': affix_id,
            'name': name,
            'meaning': meaning,
            'similar': similar_str,
            'cases': cases_str,
        }
        Affix.update(affix_data)
        
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


def list_affixes():
    """查询词缀列表"""
    try:
        affixes = Affix.select_by()
        
        data_list = []
        for item in affixes:
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
