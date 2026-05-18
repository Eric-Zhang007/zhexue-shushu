#!/usr/bin/env python3
"""玄学数术统一入口"""
import sys, os, subprocess, json, re

DIR = os.path.dirname(os.path.abspath(__file__))

SCRIPTS = {
    'bazi':     {'file':'bazi.py',     'desc':'八字排盘',       'args':'<年> <月> <日> <时> <分> <male/female>'},
    'meihua':   {'file':'meihua.py',   'desc':'梅花易数',      'args':'<a> <b> <c> 或 --time <y> <m> <d> <h>'},
    'qimen':    {'file':'qimen.py',    'desc':'奇门遁甲',      'args':'<年> <月> <日> <时> <分>'},
    'liuren':   {'file':'liuren.py',   'desc':'大六壬',        'args':'<年> <月> <日> <时> <分>'},
    'ziwei':    {'file':'ziwei.py',    'desc':'紫微斗数',      'args':'<年> <月> <日> <时> <分> <male/female>'},
    'yongshen': {'file':'yongshen.py', 'desc':'用神忌神算法',   'args':'<年干> <年支> <月干> <月支> <日干> <日支> <时干> <时支>'},
    'chenggu':  {'file':'chenggu.py',  'desc':'称骨算命',      'args':'<年干支> <农历月> <农历日> <时(0-23)>'},
}

def extract_json(text):
    m = re.search(r'\{.*\}', text, re.DOTALL)
    return json.loads(m.group()) if m else None

def run():
    if len(sys.argv) < 2 or sys.argv[1] in ('-h','--help','list'):
        print("玄学数术工具集\n")
        for k,v in SCRIPTS.items():
            print(f"  {k:10s} {v['desc']:10s}  {v['args']}")
        return
    
    method = sys.argv[1]
    if method not in SCRIPTS:
        print(f"未知: {method}"); return
    
    path = os.path.join(DIR, SCRIPTS[method]['file'])
    args = sys.argv[2:]
    r = subprocess.run([sys.executable, path]+args, capture_output=True, text=True, timeout=120)
    out = r.stdout
    
    data = extract_json(out)
    if data:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    if not data or '--text' in args:
        if out: print(out[:3000])
    if r.stderr: print(r.stderr[:500], file=sys.stderr)

if __name__ == '__main__':
    run()
