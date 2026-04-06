from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
import secrets
import signal
import subprocess
import sys
import time
import uuid
from http.cookies import SimpleCookie
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlencode, urlparse
from urllib.request import Request, urlopen


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
OUTPUT_DIR = BASE_DIR / "output"
REPORT_DIR = OUTPUT_DIR / "reports"
MEDIA_DIR = OUTPUT_DIR / "media"
ATHLETE_DIR = OUTPUT_DIR / "athletes"
PORT = 8899
RELOAD_ENV = "FIT_APP_RELOAD_CHILD"
HOST_ENV = "HOST"
PORT_ENV = "PORT"
ENABLE_RELOAD_ENV = "ENABLE_RELOAD"
SUPABASE_URL_ENV = "SUPABASE_URL"
SUPABASE_SERVICE_ROLE_KEY_ENV = "SUPABASE_SERVICE_ROLE_KEY"
SUPABASE_STORAGE_BUCKET_ENV = "SUPABASE_STORAGE_BUCKET"
DEFAULT_STORAGE_BUCKET = "training-media"
ADMIN_USERNAME_ENV = "APP_ADMIN_USERNAME"
ADMIN_PASSWORD_ENV = "APP_ADMIN_PASSWORD"
COACH_USERNAME_ENV = "APP_COACH_USERNAME"
COACH_PASSWORD_ENV = "APP_COACH_PASSWORD"
SESSION_COOKIE_NAME = "mcs_session"
SESSION_TTL_SECONDS = 60 * 60 * 12
SESSION_STORE: dict[str, dict[str, Any]] = {}


BOOTSTRAP_DATA = {
    "goals": [
        "青少年体适能启蒙",
        "体考专项提升",
        "跑步技术与耐力",
        "爆发力与灵敏性",
        "姿态矫正与基础稳定",
        "减脂与习惯养成",
    ],
    "cycles": [4, 8, 12],
    "frequencies": [1, 2, 3, 4],
    "durations": [60, 90],
    "training_types": ["早教", "私教课", "小班课/团课", "专项（闯关）训练", "跑步训练"],
    "trainee_groups": ["幼儿", "青少年", "成人"],
    "sample_profiles": [
        {
            "name": "陈一诺",
            "age": 9,
            "trainee_group": "青少年",
            "gender": "女",
            "training_goal": "青少年体适能启蒙",
            "cycle_weeks": 8,
            "sessions_per_week": 2,
            "session_duration_min": 60,
            "training_type": "私教课",
            "assessment": "基础协调较好，核心稳定偏弱，落地缓冲需要加强。",
            "needs": "希望提升运动兴趣、协调性和基础跑跳能力。",
            "constraints": "暂无伤病，注意控制单次跳跃量。",
        },
        {
            "name": "王浩然",
            "age": 14,
            "trainee_group": "青少年",
            "gender": "男",
            "training_goal": "体考专项提升",
            "cycle_weeks": 12,
            "sessions_per_week": 3,
            "session_duration_min": 90,
            "training_type": "专项（闯关）训练",
            "assessment": "1000 米后程掉速明显，立定跳远起跳效率一般。",
            "needs": "希望暑期冲刺体考成绩，同时改善跑姿和专项耐力。",
            "constraints": "右侧踝关节稳定性一般，注意热身和落地控制。",
        },
    ],
}


EXERCISE_LIBRARY = [
    {
        "name": "动物爬行接力",
        "category": "热身激活",
        "age_min": 3,
        "age_max": 8,
        "goals": ["青少年体适能启蒙", "姿态矫正与基础稳定"],
        "description": "通过熊爬、蟹步、青蛙跳等趣味移动激活肩髋核心。",
        "cues": "保持头部中立，动作节奏稳定，强调手脚协调。",
        "prescription": "3 轮，每轮 12-15 米，组间休息 30 秒。",
        "duration_min": 8,
        "video_query": "animal walk kids exercise coach demo",
    },
    {
        "name": "彩圈跳格热身",
        "category": "热身激活",
        "age_min": 3,
        "age_max": 9,
        "goals": ["青少年体适能启蒙", "爆发力与灵敏性", "减脂与习惯养成"],
        "description": "利用地面彩圈做前后跳、开合跳和单脚点圈，快速进入课堂状态。",
        "cues": "先看圈再起跳，脚尖轻触地，落地后立刻站稳。",
        "prescription": "4 轮，每轮 20-30 秒，轮间休息 20 秒。",
        "duration_min": 8,
        "video_query": "kids agility hoops warm up drill",
    },
    {
        "name": "小栏跨步走",
        "category": "热身激活",
        "age_min": 4,
        "age_max": 9,
        "goals": ["青少年体适能启蒙", "跑步技术与耐力", "姿态矫正与基础稳定"],
        "description": "用迷你栏架完成跨步走和侧向过栏，激活髋膝踝与步态节奏。",
        "cues": "抬膝过栏不过度耸肩，脚掌轻落地，保持身体直立。",
        "prescription": "3-4 轮，每轮 4-6 个栏架，双向完成。",
        "duration_min": 8,
        "video_query": "mini hurdle walk kids warm up",
    },
    {
        "name": "彩标反应跑",
        "category": "灵敏反应",
        "age_min": 6,
        "age_max": 16,
        "goals": ["青少年体适能启蒙", "爆发力与灵敏性", "体考专项提升"],
        "description": "教练发出口令或颜色指令，学员快速启动并变向触标。",
        "cues": "降低重心，第一步积极发力，转身时髋膝对齐。",
        "prescription": "6-8 组，每组 8-12 秒，组间恢复 40 秒。",
        "duration_min": 10,
        "video_query": "agility cone reaction drill youth",
    },
    {
        "name": "口令追拍启动",
        "category": "灵敏反应",
        "age_min": 4,
        "age_max": 9,
        "goals": ["青少年体适能启蒙", "爆发力与灵敏性", "减脂与习惯养成"],
        "description": "两人或小组根据口令启动追拍，发展注意力、反应和短距离加速。",
        "cues": "听清口令后再启动，第一步积极蹬地，追拍时注意减速控制。",
        "prescription": "6-8 轮，每轮 6-10 秒，轮间休息 30 秒。",
        "duration_min": 8,
        "video_query": "kids reaction chase game exercise",
    },
    {
        "name": "绳梯小步频",
        "category": "有氧协调",
        "age_min": 5,
        "age_max": 10,
        "goals": ["青少年体适能启蒙", "跑步技术与耐力", "减脂与习惯养成"],
        "description": "利用绳梯完成单格快步、开合步和左右横移，提升步频与协调。",
        "cues": "抬脚轻快，脚步进格不踩绳，眼睛看前方保持节奏。",
        "prescription": "4-6 轮，每轮 2-3 种步法，轮间休息 20 秒。",
        "duration_min": 8,
        "video_query": "ladder footwork kids training",
    },
    {
        "name": "跨栏协调跑",
        "category": "跑步技术",
        "age_min": 8,
        "age_max": 16,
        "goals": ["跑步技术与耐力", "体考专项提升"],
        "description": "利用低栏做高抬腿、并步、单脚快频等步频训练。",
        "cues": "脚踝快速触地，摆臂配合步频，躯干保持直立。",
        "prescription": "4-6 组，每组 12-18 米，重质量不求速度。",
        "duration_min": 10,
        "video_query": "youth hurdle mobility running drill",
    },
    {
        "name": "摆臂高抬腿走跑",
        "category": "跑步技术",
        "age_min": 6,
        "age_max": 9,
        "goals": ["青少年体适能启蒙", "跑步技术与耐力", "体考专项提升"],
        "description": "通过摆臂、高抬腿走和短距离走跑衔接建立基础跑姿。",
        "cues": "摆臂前后不过中线，抬膝不过度后仰，脚下快速轻触地。",
        "prescription": "4-5 轮，每轮 10-15 米，重节奏与姿态。",
        "duration_min": 8,
        "video_query": "kids running form high knees drill",
    },
    {
        "name": "药球前抛与转体抛",
        "category": "力量爆发",
        "age_min": 10,
        "age_max": 16,
        "goals": ["爆发力与灵敏性", "体考专项提升"],
        "description": "采用轻重量药球训练下肢蹬伸与躯干协同发力。",
        "cues": "先稳定站姿，再完成髋膝踝同步伸展，避免塌腰。",
        "prescription": "前抛 3 组 + 转体抛 3 组，每组 5-6 次。",
        "duration_min": 12,
        "video_query": "medicine ball throw youth training",
    },
    {
        "name": "原地蹬摆跳跃",
        "category": "力量爆发",
        "age_min": 6,
        "age_max": 9,
        "goals": ["青少年体适能启蒙", "爆发力与灵敏性", "体考专项提升"],
        "description": "通过原地摆臂蹬地、跳上标志垫和连续小跳发展基础爆发力。",
        "cues": "先摆臂再起跳，落地屈膝缓冲，连续动作保持节奏。",
        "prescription": "4 组，每组 4-6 次，组间休息 30-40 秒。",
        "duration_min": 8,
        "video_query": "kids jump landing power drill",
    },
    {
        "name": "核心死虫与侧桥",
        "category": "稳定控制",
        "age_min": 7,
        "age_max": 16,
        "goals": ["姿态矫正与基础稳定", "跑步技术与耐力", "体考专项提升"],
        "description": "强化腰盆稳定和呼吸控制，为跑跳动作打基础。",
        "cues": "肋骨回收，腰部贴稳，动作慢而准确。",
        "prescription": "死虫 3 组 x 8 次 + 侧桥 3 组 x 20-30 秒。",
        "duration_min": 10,
        "video_query": "dead bug side plank youth exercise",
    },
    {
        "name": "熊爬停稳触点",
        "category": "稳定控制",
        "age_min": 3,
        "age_max": 8,
        "goals": ["青少年体适能启蒙", "姿态矫正与基础稳定", "减脂与习惯养成"],
        "description": "熊爬前进中加入停稳和触点任务，提升肩带稳定与核心控制。",
        "cues": "膝盖离地不过高，触点时身体不摇晃，动作连续稳定。",
        "prescription": "3-4 轮，每轮 8-12 米 + 3 次停稳触点。",
        "duration_min": 8,
        "video_query": "bear crawl hold kids core drill",
    },
    {
        "name": "跪姿对侧伸展",
        "category": "稳定控制",
        "age_min": 4,
        "age_max": 9,
        "goals": ["青少年体适能启蒙", "姿态矫正与基础稳定", "跑步技术与耐力"],
        "description": "四点支撑位完成对侧手脚伸展，建立基础核心与骨盆控制。",
        "cues": "腰背平稳不过度塌陷，伸展时慢，回收时同样控制。",
        "prescription": "左右各 3 组，每组 6-8 次，组间休息 20 秒。",
        "duration_min": 8,
        "video_query": "bird dog kids exercise demo",
    },
    {
        "name": "折返跑节奏组",
        "category": "速度耐力",
        "age_min": 9,
        "age_max": 16,
        "goals": ["体考专项提升", "跑步技术与耐力"],
        "description": "设置 15 米至 25 米折返，结合间歇恢复提升心肺和变向能力。",
        "cues": "到标志点前提前减速，转身蹬地干净，呼吸有节奏。",
        "prescription": "4-6 组，每组 20-30 秒，组间休息 60-90 秒。",
        "duration_min": 14,
        "video_query": "shuttle run conditioning youth",
    },
    {
        "name": "往返接力跑",
        "category": "速度耐力",
        "age_min": 6,
        "age_max": 9,
        "goals": ["青少年体适能启蒙", "跑步技术与耐力", "减脂与习惯养成"],
        "description": "以短距离往返和接力形式提升跑动参与度与基础心肺能力。",
        "cues": "到点减速再转身，接棒或击掌后再出发，保持呼吸节奏。",
        "prescription": "4-6 轮，每轮 15-20 秒，轮间休息 30-40 秒。",
        "duration_min": 10,
        "video_query": "kids shuttle relay running drill",
    },
    {
        "name": "颜色追点游戏",
        "category": "灵敏反应",
        "age_min": 3,
        "age_max": 7,
        "goals": ["青少年体适能启蒙", "爆发力与灵敏性", "减脂与习惯养成"],
        "description": "根据颜色或数字指令快速跑向对应标志点，完成触点后回位。",
        "cues": "先听清或看清指令，再快速出发，回位后立即准备下一次。",
        "prescription": "6-10 轮，每轮 5-8 秒，轮间休息 20-30 秒。",
        "duration_min": 8,
        "video_query": "kids color reaction game drill",
    },
    {
        "name": "障碍穿越闯关",
        "category": "体考专项",
        "age_min": 4,
        "age_max": 8,
        "goals": ["青少年体适能启蒙", "爆发力与灵敏性", "体考专项提升"],
        "description": "组合钻圈、跨栏、绕桩和跳垫，提升跑跳钻爬综合能力。",
        "cues": "按顺序完成动作，绕过障碍不着急，落地与转向都先稳再快。",
        "prescription": "4-6 轮，每轮 20-30 秒，轮间休息 30 秒。",
        "duration_min": 10,
        "video_query": "kids obstacle course exercise demo",
    },
    {
        "name": "双脚并跳接沙包",
        "category": "力量爆发",
        "age_min": 5,
        "age_max": 9,
        "goals": ["青少年体适能启蒙", "爆发力与灵敏性", "减脂与习惯养成"],
        "description": "双脚连续并跳后接沙包投掷，建立基础爆发与上下肢协调。",
        "cues": "双脚同时起落，接沙包时眼睛盯住目标，落地后保持平衡。",
        "prescription": "4 组，每组 4-5 次，组间休息 30 秒。",
        "duration_min": 8,
        "video_query": "kids jump and throw coordination drill",
    },
    {
        "name": "平衡木折返挑战",
        "category": "姿态控制",
        "age_min": 4,
        "age_max": 9,
        "goals": ["青少年体适能启蒙", "姿态矫正与基础稳定", "减脂与习惯养成"],
        "description": "在低平衡木或地面平衡线上完成前进、转身和折返任务。",
        "cues": "脚跟脚尖依次落地，转身时眼睛看前方，保持身体稳定。",
        "prescription": "3-4 轮，每轮 2 次往返，轮间休息 20 秒。",
        "duration_min": 8,
        "video_query": "kids balance beam walking drill",
    },
    {
        "name": "跳绳步频控制",
        "category": "有氧协调",
        "age_min": 6,
        "age_max": 16,
        "goals": ["青少年体适能启蒙", "减脂与习惯养成", "跑步技术与耐力"],
        "description": "采用单摇、开合跳、前后步跳等方式训练节奏与心肺。",
        "cues": "手腕带绳，脚尖轻落地，保持均匀呼吸。",
        "prescription": "4 组 x 45 秒，组间调整 20 秒。",
        "duration_min": 8,
        "video_query": "jump rope footwork youth",
    },
    {
        "name": "软垫翻滚与起身",
        "category": "姿态控制",
        "age_min": 3,
        "age_max": 7,
        "goals": ["青少年体适能启蒙", "姿态矫正与基础稳定"],
        "description": "在软垫上完成前后滚动、团身和起身，建立空间感知与身体控制。",
        "cues": "下巴微收，团身滚动，起身时脚掌踩稳再站起。",
        "prescription": "3-4 轮，每轮 3-5 次，动作标准优先。",
        "duration_min": 8,
        "video_query": "kids forward roll balance movement",
    },
    {
        "name": "立定跳远技术分解",
        "category": "体考专项",
        "age_min": 10,
        "age_max": 16,
        "goals": ["体考专项提升", "爆发力与灵敏性"],
        "description": "拆分摆臂、预摆、蹬伸、落地稳定四个技术环节。",
        "cues": "摆臂主动，髋部充分后坐，落地时屈髋屈膝缓冲。",
        "prescription": "技术分解 4 组 + 完整输出 4-6 次。",
        "duration_min": 12,
        "video_query": "standing long jump technique youth",
    },
    {
        "name": "沙包投准跑跳",
        "category": "体考专项",
        "age_min": 6,
        "age_max": 9,
        "goals": ["青少年体适能启蒙", "爆发力与灵敏性", "体考专项提升"],
        "description": "结合投准、助跑和跨跳的小游戏，建立跑跳投综合能力基础。",
        "cues": "先站稳再投掷，助跑不过快，跨跳落地注意缓冲。",
        "prescription": "4 轮，每轮 3 个站点连续完成，轮间休息 30 秒。",
        "duration_min": 10,
        "video_query": "kids throw run jump coordination game",
    },
    {
        "name": "间歇跑配速练习",
        "category": "跑步专项",
        "age_min": 10,
        "age_max": 16,
        "goals": ["跑步技术与耐力", "减脂与习惯养成"],
        "description": "用 200 米或 400 米区间做配速控制和恢复管理。",
        "cues": "前半程留有余量，中后程稳定摆臂，关注步幅和步频一致性。",
        "prescription": "200 米 x 4-6 组，配速稳定，组间慢走恢复。",
        "duration_min": 16,
        "video_query": "interval running pace drill youth",
    },
    {
        "name": "节奏绕桩跑",
        "category": "跑步专项",
        "age_min": 7,
        "age_max": 9,
        "goals": ["跑步技术与耐力", "青少年体适能启蒙", "减脂与习惯养成"],
        "description": "通过绕桩、加速和回位跑动建立跑线意识、节奏转换和持续移动能力。",
        "cues": "绕桩时重心稍低，步伐连续，回位后快速整理呼吸。",
        "prescription": "5-6 组，每组 12-18 秒，组间休息 30 秒。",
        "duration_min": 10,
        "video_query": "kids cone running drill rhythm",
    },
    {
        "name": "平衡垫单腿稳定",
        "category": "姿态控制",
        "age_min": 5,
        "age_max": 16,
        "goals": ["姿态矫正与基础稳定", "青少年体适能启蒙"],
        "description": "在不稳定平面完成单腿站立、触点、抛接球。",
        "cues": "骨盆保持水平，膝盖对准脚尖，眼睛平视前方。",
        "prescription": "左右各 3 组，每组 20-30 秒，逐步增加干扰。",
        "duration_min": 8,
        "video_query": "balance pad single leg youth",
    },
    {
        "name": "趣味循环减脂站",
        "category": "代谢循环",
        "age_min": 8,
        "age_max": 16,
        "goals": ["减脂与习惯养成", "青少年体适能启蒙"],
        "description": "组合开合跳、波比简化版、战绳、登阶等循环站。",
        "cues": "控制动作质量，采用短间歇快轮转，注意补水。",
        "prescription": "5 站循环 3 轮，每站 30-40 秒。",
        "duration_min": 15,
        "video_query": "kids fitness circuit training demo",
    },
    {
        "name": "数字站点闯关",
        "category": "代谢循环",
        "age_min": 5,
        "age_max": 9,
        "goals": ["减脂与习惯养成", "青少年体适能启蒙", "爆发力与灵敏性"],
        "description": "把跳跃、爬行、搬运和折返整合成数字闯关，提高活动量和参与度。",
        "cues": "按站点顺序完成，动作到位再换站，保持课堂秩序和节奏。",
        "prescription": "4 站循环 3 轮，每站 30 秒，站间休息 15 秒。",
        "duration_min": 12,
        "video_query": "kids circuit stations exercise game",
    },
    {
        "name": "放松拉伸与呼吸恢复",
        "category": "整理放松",
        "age_min": 3,
        "age_max": 16,
        "goals": [
            "青少年体适能启蒙",
            "体考专项提升",
            "跑步技术与耐力",
            "爆发力与灵敏性",
            "姿态矫正与基础稳定",
            "减脂与习惯养成",
        ],
        "description": "针对小腿、髋屈肌、腘绳肌、胸椎做拉伸与呼吸回落。",
        "cues": "呼气放松，动作保持 20 到 30 秒，不做弹震式拉伸。",
        "prescription": "4-6 个部位，单个动作保持 20-30 秒。",
        "duration_min": 6,
        "video_query": "cool down stretching youth athletes",
    },
]

AGE_FRAMEWORKS: list[dict[str, Any]] = [
    {
        "code": "3-6",
        "label": "3-6岁 启蒙感知期",
        "age_min": 3,
        "age_max": 6,
        "session_patterns": {
            60: [12, 12, 14, 12, 10],
            90: [15, 15, 18, 16, 14, 12],
        },
        "block_names_60": ["趣味热身", "基础动作", "协调游戏", "轻体能", "放松整理"],
        "block_names_90": ["趣味热身", "基础动作", "协调游戏", "轻力量", "轻体能", "放松整理"],
        "intensity": "RPE 4-6，以兴趣、参与和动作感知为主。",
        "rest": "多采用站内轮换和游戏过渡，组间 20-40 秒。",
        "key_points": ["培养运动兴趣", "建立基本跑跳投爬", "强调安全感和规则意识"],
        "priority_categories": ["热身激活", "有氧协调", "姿态控制", "稳定控制", "整理放松"],
    },
    {
        "code": "7-9",
        "label": "7-9岁 基础发展期",
        "age_min": 7,
        "age_max": 9,
        "session_patterns": {
            60: [10, 12, 15, 13, 10],
            90: [12, 15, 18, 15, 18, 12],
        },
        "block_names_60": ["动态热身", "动作技术", "主项能力", "基础体能", "放松整理"],
        "block_names_90": ["动态热身", "动作技术", "主项能力", "力量稳定", "基础体能", "放松整理"],
        "intensity": "RPE 5-6，强调动作质量和节奏控制。",
        "rest": "主项组间 30-60 秒，技术段按动作完成质量灵活调整。",
        "key_points": ["发展协调与节奏", "建立基础力量控制", "开始形成专项前置能力"],
        "priority_categories": ["热身激活", "灵敏反应", "稳定控制", "有氧协调", "整理放松"],
    },
    {
        "code": "10-12",
        "label": "10-12岁 技能衔接期",
        "age_min": 10,
        "age_max": 12,
        "session_patterns": {
            60: [10, 10, 18, 12, 10],
            90: [12, 12, 22, 16, 16, 12],
        },
        "block_names_60": ["专项热身", "技术修正", "主训练段", "体能补充", "恢复整理"],
        "block_names_90": ["专项热身", "技术修正", "主训练段", "辅助能力", "体能补充", "恢复整理"],
        "intensity": "RPE 5-7，主训练段逐步提高输出。",
        "rest": "主项组间 45-90 秒，速度类动作保证充分恢复。",
        "key_points": ["提高动作效率", "强化核心与下肢控制", "建立专项训练耐受"],
        "priority_categories": ["跑步技术", "体考专项", "稳定控制", "速度耐力", "整理放松"],
    },
    {
        "code": "13-16",
        "label": "13-16岁 专项提升期",
        "age_min": 13,
        "age_max": 16,
        "session_patterns": {
            60: [10, 10, 20, 10, 10],
            90: [12, 12, 24, 16, 14, 12],
        },
        "block_names_60": ["专项热身", "技术打磨", "主专项训练", "体能强化", "恢复整理"],
        "block_names_90": ["专项热身", "技术打磨", "主专项训练", "力量爆发", "体能强化", "恢复整理"],
        "intensity": "RPE 6-8，保证主专项训练刺激和恢复平衡。",
        "rest": "速度爆发类动作 60-120 秒，耐力类动作按配速目标恢复。",
        "key_points": ["围绕目标成绩推进", "建立专项技术稳定性", "兼顾恢复和测试转化"],
        "priority_categories": ["跑步专项", "体考专项", "力量爆发", "速度耐力", "整理放松"],
    },
    {
        "code": "adult",
        "label": "成人训练提升期",
        "age_min": 17,
        "age_max": 99,
        "session_patterns": {
            60: [10, 10, 20, 10, 10],
            90: [12, 12, 24, 16, 14, 12],
        },
        "block_names_60": ["专项热身", "技术调整", "主训练段", "体能强化", "恢复整理"],
        "block_names_90": ["专项热身", "技术调整", "主训练段", "辅助力量", "体能强化", "恢复整理"],
        "intensity": "RPE 5-8，兼顾动作质量、训练刺激和恢复管理。",
        "rest": "力量速度类动作 45-120 秒，心肺类动作按目标强度管理恢复。",
        "key_points": ["围绕训练目标推进", "强化动作质量与体能表现", "兼顾恢复和持续性"],
        "priority_categories": ["跑步专项", "力量爆发", "稳定控制", "速度耐力", "整理放松"],
    },
]

GOAL_FRAMEWORKS: dict[str, dict[str, Any]] = {
    "青少年体适能启蒙": {
        "cycle_focus": {
            "3-6": ["兴趣建立", "基本位移", "平衡协调", "体能体验"],
            "7-9": ["动作启蒙", "协调节奏", "基础力量", "综合体能"],
            "10-12": ["动作重建", "综合协调", "控制输出", "能力巩固"],
            "13-16": ["基础体能", "动作效率", "综合能力", "稳定输出"],
        },
        "primary_categories": ["热身激活", "有氧协调", "姿态控制", "稳定控制"],
        "coach_goal": "让学员愿意动、会动、能持续参与训练。",
    },
    "体考专项提升": {
        "cycle_focus": {
            "3-6": ["兴趣建立", "跑跳启蒙", "规则意识", "综合体能"],
            "7-9": ["基础跑跳", "协调支撑", "初级专项", "测试体验"],
            "10-12": ["技术评估", "基础力量", "专项能力", "模拟测试"],
            "13-16": ["测试诊断", "专项力量", "成绩转化", "模拟冲刺"],
        },
        "primary_categories": ["体考专项", "跑步技术", "力量爆发", "速度耐力"],
        "coach_goal": "围绕考试项目提升技术完成度与成绩表现。",
    },
    "跑步技术与耐力": {
        "cycle_focus": {
            "3-6": ["摆臂节奏", "趣味跑动", "呼吸感知", "连续参与"],
            "7-9": ["跑姿启蒙", "步频建立", "基础有氧", "配速体验"],
            "10-12": ["跑姿矫正", "步频提升", "有氧耐力", "配速稳定"],
            "13-16": ["技术评估", "步幅步频", "专项耐力", "节奏输出"],
        },
        "primary_categories": ["跑步技术", "跑步专项", "速度耐力", "稳定控制"],
        "coach_goal": "优化跑姿效率并逐步提高持续跑与间歇跑能力。",
    },
    "爆发力与灵敏性": {
        "cycle_focus": {
            "3-6": ["快速反应", "趣味跳跃", "空间感知", "连贯动作"],
            "7-9": ["反应启动", "多向移动", "基础弹跳", "速度衔接"],
            "10-12": ["激活反应", "加速启动", "多向变向", "输出整合"],
            "13-16": ["启动速度", "爆发输出", "变向效率", "专项转化"],
        },
        "primary_categories": ["灵敏反应", "力量爆发", "体考专项", "速度耐力"],
        "coach_goal": "提高启动、变向和爆发动作的效率与质量。",
    },
    "姿态矫正与基础稳定": {
        "cycle_focus": {
            "3-6": ["身体认知", "平衡稳定", "简单控制", "动作连贯"],
            "7-9": ["呼吸控制", "姿态对齐", "单侧稳定", "动作整合"],
            "10-12": ["呼吸重建", "核心稳定", "单侧控制", "动作整合"],
            "13-16": ["稳定评估", "核心控制", "姿态修正", "专项衔接"],
        },
        "primary_categories": ["姿态控制", "稳定控制", "热身激活", "整理放松"],
        "coach_goal": "改善姿态代偿并建立稳定的动作基础。",
    },
    "减脂与习惯养成": {
        "cycle_focus": {
            "3-6": ["兴趣建立", "活动量提升", "规则感知", "持续参与"],
            "7-9": ["运动兴趣", "基础代谢", "习惯建立", "活动维持"],
            "10-12": ["运动兴趣", "基础代谢", "训练自律", "习惯固化"],
            "13-16": ["代谢提升", "训练执行", "持续管理", "生活方式固化"],
        },
        "primary_categories": ["代谢循环", "有氧协调", "跑步专项", "整理放松"],
        "coach_goal": "通过可持续训练提升活动量、代谢和执行习惯。",
    },
}

THEME_TRACKS = {
    "3-6": ["森林探险", "彩虹闯关", "小勇士课堂", "平衡星球"],
    "7-9": ["跑动主线", "跳跃主线", "投掷主线", "支撑主线"],
}

FOCUS_CATEGORY_MAP = {
    "兴趣建立": ["热身激活", "灵敏反应", "有氧协调"],
    "基本位移": ["热身激活", "跑步技术", "体考专项"],
    "平衡协调": ["姿态控制", "稳定控制", "有氧协调"],
    "体能体验": ["有氧协调", "代谢循环", "速度耐力"],
    "动作启蒙": ["跑步技术", "姿态控制", "有氧协调"],
    "协调节奏": ["有氧协调", "灵敏反应", "跑步技术"],
    "基础力量": ["力量爆发", "稳定控制", "姿态控制"],
    "综合体能": ["速度耐力", "代谢循环", "有氧协调"],
    "基础跑跳": ["跑步技术", "力量爆发", "体考专项"],
    "协调支撑": ["稳定控制", "姿态控制", "灵敏反应"],
    "初级专项": ["体考专项", "跑步技术", "力量爆发"],
    "测试体验": ["体考专项", "速度耐力", "跑步专项"],
}

TRACK_EXERCISE_HINTS = {
    "森林探险": ["动物爬行接力", "障碍穿越闯关", "熊爬停稳触点"],
    "彩虹闯关": ["彩圈跳格热身", "颜色追点游戏", "绳梯小步频"],
    "小勇士课堂": ["口令追拍启动", "障碍穿越闯关", "双脚并跳接沙包"],
    "平衡星球": ["平衡木折返挑战", "平衡垫单腿稳定", "跪姿对侧伸展"],
    "跑动主线": ["摆臂高抬腿走跑", "跨栏协调跑", "节奏绕桩跑", "往返接力跑"],
    "跳跃主线": ["原地蹬摆跳跃", "双脚并跳接沙包", "彩圈跳格热身", "障碍穿越闯关"],
    "投掷主线": ["沙包投准跑跳", "双脚并跳接沙包", "障碍穿越闯关"],
    "支撑主线": ["熊爬停稳触点", "跪姿对侧伸展", "平衡木折返挑战", "核心死虫与侧桥"],
}

TRACK_PHASE_EXERCISE_HINTS = {
    ("跑动主线", "主项能力"): ["节奏绕桩跑", "往返接力跑", "摆臂高抬腿走跑"],
    ("跳跃主线", "主项能力"): ["原地蹬摆跳跃", "双脚并跳接沙包", "彩圈跳格热身"],
    ("投掷主线", "主项能力"): ["沙包投准跑跳", "障碍穿越闯关", "双脚并跳接沙包"],
    ("支撑主线", "主项能力"): ["熊爬停稳触点", "跪姿对侧伸展", "平衡垫单腿稳定"],
    ("森林探险", "协调游戏"): ["障碍穿越闯关", "动物爬行接力", "熊爬停稳触点"],
    ("彩虹闯关", "协调游戏"): ["颜色追点游戏", "彩圈跳格热身", "绳梯小步频"],
    ("小勇士课堂", "协调游戏"): ["口令追拍启动", "障碍穿越闯关", "双脚并跳接沙包"],
    ("平衡星球", "协调游戏"): ["平衡木折返挑战", "平衡垫单腿稳定", "跪姿对侧伸展"],
}

THEME_STORYLINES = {
    "森林探险": "把课堂带成一场森林探险，教练用“钻树林、过小桥、翻山坡”的提示带孩子持续投入。",
    "彩虹闯关": "把动作串成颜色闯关，教练用“找到颜色、跳进彩圈、冲过终点”的语句提升参与感。",
    "小勇士课堂": "把训练包装成小勇士任务，鼓励孩子完成追击、跳跃和闯关挑战，建立勇敢与秩序感。",
    "平衡星球": "把课堂讲成登陆平衡星球，强调慢、稳、准，让孩子在控制身体中获得成就感。",
    "跑动主线": "本节课围绕跑动主线推进，重点提升跑姿、步频和持续跑动能力。",
    "跳跃主线": "本节课围绕跳跃主线推进，重点发展摆臂、蹬地和落地缓冲能力。",
    "投掷主线": "本节课围绕投掷主线推进，重点建立上肢发力、躯干传导和跑跳投衔接。",
    "支撑主线": "本节课围绕支撑主线推进，重点提升稳定控制、姿态质量和基础力量承托。",
}

SESSION_VARIANTS = {
    "3-6": ["认识任务", "完成闯关", "连贯挑战", "成果展示"],
    "7-9": ["技术建立", "节奏推进", "组合输出", "巩固展示"],
    "10-12": ["技术建立", "负荷推进", "专项整合", "巩固输出"],
    "13-16": ["评估建立", "专项推进", "强化输出", "模拟检验"],
}

THEME_EQUIPMENT = {
    "森林探险": ["爬行垫", "标志桶", "迷你栏架", "平衡步道"],
    "彩虹闯关": ["彩圈", "颜色标志碟", "绳梯", "软垫"],
    "小勇士课堂": ["障碍架", "标志桶", "沙包", "跳垫"],
    "平衡星球": ["平衡木", "平衡垫", "软垫", "轻球"],
    "跑动主线": ["标志桶", "绳梯", "迷你栏架", "节拍器"],
    "跳跃主线": ["彩圈", "跳垫", "沙包", "标志碟"],
    "投掷主线": ["沙包", "轻药球", "目标框", "标志线"],
    "支撑主线": ["软垫", "平衡垫", "弹力带", "小栏架"],
}

COACH_CUE_LIBRARY = {
    "森林探险": ["小脚轻轻走过小桥", "钻过树林后马上站稳", "看到终点再加速冲过去"],
    "彩虹闯关": ["找到颜色再出发", "跳进圈里脚步要轻", "完成一个颜色马上准备下一个"],
    "小勇士课堂": ["听到口令才行动", "落地先稳住再继续", "完成挑战后大声报到"],
    "平衡星球": ["慢慢走也算成功", "身体像小树一样站稳", "转身时眼睛一直看前方"],
    "跑动主线": ["摆臂带着脚步走", "脚下轻快不要拖地", "过标志点后继续保持节奏"],
    "跳跃主线": ["先摆臂再起跳", "落地像小猫一样轻", "跳完马上准备下一次"],
    "投掷主线": ["先看目标再发力", "蹬地后把力量送出去", "投完保持身体稳定"],
    "支撑主线": ["肚子收紧像小桥", "动作慢一点更标准", "左右都要一样稳"],
}


def ensure_dirs() -> None:
    for path in (OUTPUT_DIR, REPORT_DIR, MEDIA_DIR, ATHLETE_DIR):
        path.mkdir(parents=True, exist_ok=True)


def read_static_file(name: str) -> bytes:
    path = STATIC_DIR / name
    if not path.exists():
        raise FileNotFoundError(name)
    return path.read_bytes()


def sanitize_filename(text: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff_-]+", "-", text).strip("-")
    return value or "record"


def supabase_url() -> str:
    return os.environ.get(SUPABASE_URL_ENV, "").strip().rstrip("/")


def supabase_service_key() -> str:
    return os.environ.get(SUPABASE_SERVICE_ROLE_KEY_ENV, "").strip()


def supabase_storage_bucket() -> str:
    return os.environ.get(SUPABASE_STORAGE_BUCKET_ENV, DEFAULT_STORAGE_BUCKET).strip()


def supabase_enabled() -> bool:
    return bool(supabase_url() and supabase_service_key())


def configured_users() -> list[dict[str, str]]:
    return [
        {
            "username": os.environ.get(ADMIN_USERNAME_ENV, "admin").strip() or "admin",
            "password": os.environ.get(ADMIN_PASSWORD_ENV, "admin123456").strip() or "admin123456",
            "role": "admin",
            "label": "管理员",
        },
        {
            "username": os.environ.get(COACH_USERNAME_ENV, "coach").strip() or "coach",
            "password": os.environ.get(COACH_PASSWORD_ENV, "coach123456").strip() or "coach123456",
            "role": "coach",
            "label": "教练",
        },
    ]


def role_label(role: str) -> str:
    return "管理员" if role == "admin" else "教练"


def auth_identity_payload(user: dict[str, str]) -> dict[str, str]:
    return {"username": user["username"], "role": user["role"], "role_label": role_label(user["role"])}


def create_session(user: dict[str, str]) -> str:
    token = secrets.token_urlsafe(32)
    SESSION_STORE[token] = {
        "username": user["username"],
        "role": user["role"],
        "expires_at": time.time() + SESSION_TTL_SECONDS,
    }
    return token


def session_from_token(token: str) -> dict[str, Any] | None:
    session = SESSION_STORE.get(token)
    if not session:
        return None
    if session.get("expires_at", 0) < time.time():
        SESSION_STORE.pop(token, None)
        return None
    session["expires_at"] = time.time() + SESSION_TTL_SECONDS
    return session


def parse_cookie_header(header: str | None) -> SimpleCookie[str]:
    cookie = SimpleCookie()
    if header:
        cookie.load(header)
    return cookie


def current_identity_from_headers(headers: Any) -> dict[str, Any] | None:
    cookie = parse_cookie_header(headers.get("Cookie"))
    token = cookie.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    return session_from_token(token.value)


def authenticate_user(username: str, password: str) -> dict[str, str] | None:
    normalized_username = username.strip()
    normalized_password = password.strip()
    for user in configured_users():
        if user["username"] == normalized_username and user["password"] == normalized_password:
            return user
    return None


def session_cookie(token: str) -> str:
    return f"{SESSION_COOKIE_NAME}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={SESSION_TTL_SECONDS}"


def clear_session_cookie() -> str:
    return f"{SESSION_COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"


def supabase_request(
    method: str,
    path: str,
    *,
    query: dict[str, Any] | None = None,
    json_body: dict[str, Any] | list[dict[str, Any]] | None = None,
    data: bytes | None = None,
    extra_headers: dict[str, str] | None = None,
) -> Any:
    if not supabase_enabled():
        raise RuntimeError("Supabase 环境变量未配置")
    url = f"{supabase_url()}{path}"
    if query:
        cleaned = {key: value for key, value in query.items() if value is not None}
        url = f"{url}?{urlencode(cleaned)}"

    headers = {
        "apikey": supabase_service_key(),
        "Authorization": f"Bearer {supabase_service_key()}",
    }
    if extra_headers:
        headers.update(extra_headers)

    payload: bytes | None = data
    if json_body is not None:
        payload = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=payload, headers=headers, method=method.upper())
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read()
            content_type = response.headers.get("Content-Type", "")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Supabase 请求失败: {exc.code} {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Supabase 连接失败: {exc.reason}") from exc

    if not body:
        return None
    if "application/json" in content_type:
        return json.loads(body.decode("utf-8"))
    return body


def athlete_to_db_row(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": profile["id"],
        "created_at": profile.get("created_at"),
        "updated_at": profile.get("updated_at"),
        "name": profile.get("name", "未命名学员"),
        "age": profile.get("age"),
        "trainee_group": profile.get("trainee_group"),
        "gender": profile.get("gender"),
        "height": profile.get("height"),
        "weight": profile.get("weight"),
        "school": profile.get("school"),
        "grade": profile.get("grade"),
        "guardian_name": profile.get("guardian_name"),
        "guardian_phone": profile.get("guardian_phone"),
        "training_goal": profile.get("training_goal"),
        "cycle_weeks": profile.get("cycle_weeks"),
        "sessions_per_week": profile.get("sessions_per_week"),
        "session_duration_min": profile.get("session_duration_min"),
        "training_type": profile.get("training_type"),
        "assessment": profile.get("assessment"),
        "needs": profile.get("needs"),
        "constraints": profile.get("constraints"),
        "training_experience": profile.get("training_experience"),
        "sports_preferences": profile.get("sport_preference", ""),
        "available_schedule": profile.get("available_schedule"),
        "baseline_metrics": profile.get("baseline_metrics"),
        "medical_history": profile.get("medical_history"),
        "injury_history": profile.get("injury_history"),
        "personality_notes": profile.get("personality_notes"),
        "raw": profile,
    }


def athlete_from_db_row(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("raw") or {}
    profile = {
        "id": row.get("id", raw.get("id", "")),
        "name": row.get("name", raw.get("name", "未命名学员")),
        "age": row.get("age", raw.get("age", "")),
        "trainee_group": row.get("trainee_group", raw.get("trainee_group", "青少年")),
        "gender": row.get("gender", raw.get("gender", "")),
        "height": row.get("height", raw.get("height", "")),
        "weight": row.get("weight", raw.get("weight", "")),
        "school": row.get("school", raw.get("school", "")),
        "grade": row.get("grade", raw.get("grade", "")),
        "guardian_name": row.get("guardian_name", raw.get("guardian_name", "")),
        "guardian_phone": row.get("guardian_phone", raw.get("guardian_phone", "")),
        "training_experience": row.get("training_experience", raw.get("training_experience", "")),
        "sport_preference": row.get("sports_preferences", raw.get("sport_preference", "")),
        "available_schedule": row.get("available_schedule", raw.get("available_schedule", "")),
        "medical_history": row.get("medical_history", raw.get("medical_history", "")),
        "injury_history": row.get("injury_history", raw.get("injury_history", "")),
        "baseline_metrics": row.get("baseline_metrics", raw.get("baseline_metrics", "")),
        "personality_notes": row.get("personality_notes", raw.get("personality_notes", "")),
        "training_type": row.get("training_type", raw.get("training_type", "")),
        "training_goal": row.get("training_goal", raw.get("training_goal", "")),
        "cycle_weeks": row.get("cycle_weeks", raw.get("cycle_weeks", 8)),
        "sessions_per_week": row.get("sessions_per_week", raw.get("sessions_per_week", 2)),
        "session_duration_min": row.get("session_duration_min", raw.get("session_duration_min", 60)),
        "assessment": row.get("assessment", raw.get("assessment", "")),
        "needs": row.get("needs", raw.get("needs", "")),
        "constraints": row.get("constraints", raw.get("constraints", "")),
        "created_at": row.get("created_at", raw.get("created_at", "")),
        "updated_at": row.get("updated_at", raw.get("updated_at", "")),
    }
    return profile


def report_to_db_row(report: dict[str, Any]) -> dict[str, Any]:
    athlete = report.get("athlete", {})
    session = report.get("session", {})
    plan_athlete = report.get("plan", {}).get("athlete", {})
    return {
        "id": report["id"],
        "created_at": report.get("created_at"),
        "athlete_id": athlete.get("id", ""),
        "athlete_name": athlete.get("name", ""),
        "session_date": session.get("date", ""),
        "goal": plan_athlete.get("goal", athlete.get("goal", athlete.get("training_goal", ""))),
        "engagement": session.get("engagement", ""),
        "parent_summary": report.get("parent_summary", ""),
        "report": report,
    }


def report_from_db_row(row: dict[str, Any]) -> dict[str, Any]:
    report = row.get("report") or {}
    if isinstance(report, dict):
        report.setdefault("id", row.get("id", ""))
        report.setdefault("created_at", row.get("created_at", ""))
        report.setdefault("parent_summary", row.get("parent_summary", ""))
    return report


def supabase_delete_storage_objects(paths: list[str]) -> None:
    unique_paths = [path for path in dict.fromkeys(paths) if path]
    if not unique_paths:
        return
    for path in unique_paths:
        supabase_request(
            "DELETE",
            f"/storage/v1/object/{quote(supabase_storage_bucket(), safe='')}/{quote(path, safe='/')}",
        )


def supabase_storage_path_from_url(url: str) -> str:
    prefix = f"{supabase_url()}/storage/v1/object/public/{supabase_storage_bucket()}/"
    if url.startswith(prefix):
        return unquote(url.removeprefix(prefix))
    return ""


def delete_media_items(media_items: list[dict[str, Any]]) -> None:
    cloud_paths: list[str] = []
    for item in media_items:
        url = item.get("url", "")
        cloud_path = supabase_storage_path_from_url(url) if supabase_enabled() else ""
        if cloud_path:
            cloud_paths.append(cloud_path)
            continue
        if url.startswith("/media/"):
            filename = unquote(url.removeprefix("/media/"))
            target = MEDIA_DIR / filename
            if target.exists():
                target.unlink()
    if supabase_enabled() and cloud_paths:
        supabase_delete_storage_objects(cloud_paths)


def save_athlete_profile_cloud(profile: dict[str, Any]) -> dict[str, Any]:
    saved = supabase_request(
        "POST",
        "/rest/v1/athletes",
        query={"on_conflict": "id"},
        json_body=athlete_to_db_row(profile),
        extra_headers={"Prefer": "resolution=merge-duplicates,return=representation"},
    )
    if isinstance(saved, list) and saved:
        return athlete_from_db_row(saved[0])
    return profile


def delete_athlete_profile_cloud(athlete_id: str) -> dict[str, Any]:
    athlete_rows = supabase_request(
        "GET",
        "/rest/v1/athletes",
        query={"select": "*", "id": f"eq.{athlete_id}", "limit": "1"},
    )
    athlete_row = athlete_rows[0] if athlete_rows else None
    report_rows = supabase_request(
        "GET",
        "/rest/v1/reports",
        query={"select": "*", "athlete_id": f"eq.{athlete_id}", "limit": "1000"},
    )
    reports = [report_from_db_row(row) for row in report_rows or []]
    for report in reports:
        delete_media_items(report.get("media", []))
    supabase_request("DELETE", "/rest/v1/reports", query={"athlete_id": f"eq.{athlete_id}"}, extra_headers={"Prefer": "return=minimal"})
    supabase_request("DELETE", "/rest/v1/athletes", query={"id": f"eq.{athlete_id}"}, extra_headers={"Prefer": "return=minimal"})
    if athlete_row:
        return athlete_from_db_row(athlete_row)
    return {"id": athlete_id}


def list_athlete_profiles_cloud(limit: int = 10) -> list[dict[str, Any]]:
    rows = supabase_request(
        "GET",
        "/rest/v1/athletes",
        query={"select": "*", "order": "updated_at.desc", "limit": str(limit)},
    )
    profiles = []
    for row in rows or []:
        profile = athlete_from_db_row(row)
        profiles.append(
            {
                "id": profile.get("id", ""),
                "name": profile.get("name", "未命名学员"),
                "age": profile.get("age", ""),
                "trainee_group": profile.get("trainee_group", "青少年"),
                "gender": profile.get("gender", ""),
                "guardian_phone": profile.get("guardian_phone", ""),
                "goal": profile.get("training_goal", ""),
                "training_type": profile.get("training_type", ""),
                "session_duration_min": profile.get("session_duration_min", 60),
                "updated_at": profile.get("updated_at", ""),
                "profile": profile,
            }
        )
    return profiles


def delete_report_cloud(report_id: str) -> dict[str, Any]:
    rows = supabase_request(
        "GET",
        "/rest/v1/reports",
        query={"select": "*", "id": f"eq.{report_id}", "limit": "1"},
    )
    if not rows:
        raise ValueError("未找到对应的训练报告")
    report = report_from_db_row(rows[0])
    delete_media_items(report.get("media", []))
    supabase_request("DELETE", "/rest/v1/reports", query={"id": f"eq.{report_id}"}, extra_headers={"Prefer": "return=minimal"})
    return report


def recent_reports_cloud(limit: int = 6) -> list[dict[str, Any]]:
    rows = supabase_request(
        "GET",
        "/rest/v1/reports",
        query={"select": "*", "order": "created_at.desc", "limit": str(limit)},
    )
    reports = []
    for row in rows or []:
        data = report_from_db_row(row)
        reports.append(
            {
                "id": data.get("id", ""),
                "athlete_name": data.get("athlete", {}).get("name", row.get("athlete_name", "未命名学员")),
                "goal": data.get("plan", {}).get("athlete", {}).get("goal", row.get("goal", "")),
                "date": data.get("session", {}).get("date", row.get("session_date", "")),
                "summary": data.get("parent_friendly", {}).get("headline", row.get("parent_summary", "")),
                "media_count": len(data.get("media", [])),
                "engagement": data.get("session", {}).get("engagement", row.get("engagement", "")),
            }
        )
    return reports


def athlete_report_history_cloud(athlete: dict[str, Any], limit: int = 6) -> list[dict[str, Any]]:
    athlete_id = athlete.get("id", "")
    athlete_name = athlete.get("name", "")
    query: dict[str, Any] = {"select": "*", "order": "created_at.desc", "limit": str(limit)}
    if athlete_id:
        query["athlete_id"] = f"eq.{athlete_id}"
    elif athlete_name:
        query["athlete_name"] = f"eq.{athlete_name}"
    else:
        return []
    rows = supabase_request("GET", "/rest/v1/reports", query=query)
    history = [report_from_db_row(row) for row in rows or []]
    return list(reversed(history))


def upload_media_to_supabase(item: dict[str, Any], athlete_name: str, index: int) -> dict[str, Any]:
    raw = item.get("data_url", "")
    match = re.match(r"data:(.*?);base64,(.*)", raw)
    if not match:
        raise ValueError("媒体数据格式不正确")
    mime_type, encoded = match.groups()
    extension = mimetypes.guess_extension(mime_type) or (".bin" if "/" not in mime_type else f".{mime_type.split('/')[-1]}")
    athlete_slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", athlete_name).strip("-") or "athlete"
    filename = f"{athlete_slug}/{datetime.now().strftime('%Y%m%d-%H%M%S')}-{index}-{uuid.uuid4().hex[:8]}{extension}"
    binary = base64.b64decode(encoded)
    supabase_request(
        "POST",
        f"/storage/v1/object/{quote(supabase_storage_bucket(), safe='')}/{quote(filename, safe='/')}",
        data=binary,
        extra_headers={"Content-Type": mime_type, "x-upsert": "true"},
    )
    public_url = f"{supabase_url()}/storage/v1/object/public/{quote(supabase_storage_bucket(), safe='')}/{quote(filename, safe='/')}"
    return {
        "name": item.get("name", filename.rsplit("/", 1)[-1]),
        "mime_type": mime_type,
        "url": public_url,
        "kind": "video" if mime_type.startswith("video/") else "image",
    }


def age_band(age: int) -> str:
    return age_framework(age)["label"]


def age_framework(age: int) -> dict[str, Any]:
    for framework in AGE_FRAMEWORKS:
        if framework["age_min"] <= age <= framework["age_max"]:
            return framework
    return AGE_FRAMEWORKS[-1]


def video_links(query: str) -> list[dict[str, str]]:
    encoded = quote(query)
    return [
        {"label": "小红书示范", "url": f"https://www.xiaohongshu.com/search_result?keyword={encoded}"},
        {"label": "抖音示范", "url": f"https://www.douyin.com/search/{encoded}"},
    ]


def pick_exercises(goal: str, age: int, limit: int = 8) -> list[dict[str, Any]]:
    framework = age_framework(age)
    goal_rules = GOAL_FRAMEWORKS.get(goal, {})
    matches = [
        item
        for item in EXERCISE_LIBRARY
        if item["age_min"] <= age <= item["age_max"] and goal in item["goals"]
    ]
    prioritized_categories = goal_rules.get("primary_categories", []) + framework.get("priority_categories", [])
    prioritized_matches = sorted(
        matches,
        key=lambda item: (
            0 if item["category"] in prioritized_categories else 1,
            prioritized_categories.index(item["category"]) if item["category"] in prioritized_categories else 999,
            item["duration_min"],
        ),
    )
    fallback = [
        item
        for item in EXERCISE_LIBRARY
        if item["age_min"] <= age <= item["age_max"] and item["category"] in {"热身激活", "稳定控制", "整理放松"}
    ]
    source = prioritized_matches + fallback
    chosen = []
    used_categories: set[str] = set()
    for item in source:
        if item["category"] in used_categories:
            continue
        if item not in chosen:
            chosen.append(item)
            used_categories.add(item["category"])
        if len(chosen) >= limit:
            break
    for item in source:
        if item not in chosen:
            chosen.append(item)
        if len(chosen) >= limit:
            break
    cooldown = next(
        (
            item
            for item in EXERCISE_LIBRARY
            if item["age_min"] <= age <= item["age_max"] and item["category"] == "整理放松"
        ),
        None,
    )
    if cooldown and cooldown not in chosen:
        if len(chosen) >= limit:
            chosen[-1] = cooldown
        else:
            chosen.append(cooldown)
    return chosen[:limit]


def generate_cycle_focus(goal: str, weeks: int, age: int) -> list[str]:
    age_code = age_framework(age)["code"]
    goal_rules = GOAL_FRAMEWORKS.get(goal, {})
    base = goal_rules.get("cycle_focus", {}).get(age_code, ["基础评估", "动作建立", "能力提升", "巩固输出"])
    return [base[min(index * len(base) // weeks, len(base) - 1)] for index in range(weeks)]


def training_emphasis(goal: str) -> dict[str, str]:
    mapping = {
        "青少年体适能启蒙": {"main": "趣味性与基础动作", "support": "协调、平衡、跑跳投综合刺激"},
        "体考专项提升": {"main": "专项成绩与技术打磨", "support": "速度耐力、力量输出和测试适应"},
        "跑步技术与耐力": {"main": "跑姿效率与配速能力", "support": "步频、呼吸、节奏稳定"},
        "爆发力与灵敏性": {"main": "启动与快速变向", "support": "反应速度、蹬伸效率和敏捷转换"},
        "姿态矫正与基础稳定": {"main": "身体控制与姿态优化", "support": "核心稳定、单侧控制和呼吸整合"},
        "减脂与习惯养成": {"main": "运动消耗与习惯培养", "support": "持续参与度、代谢循环和家庭配合"},
    }
    return mapping.get(goal, {"main": "基础体能", "support": "动作质量与训练习惯"})


def theme_track(age: int, focus: str, offset: int) -> str:
    framework = age_framework(age)
    tracks = THEME_TRACKS.get(framework["code"], [])
    if not tracks:
        return focus
    return tracks[offset % len(tracks)]


def storyline_for_track(track: str, focus: str) -> str:
    return THEME_STORYLINES.get(track, f"本节课围绕“{focus}”推进，教练可用简洁口令保持课堂节奏与参与度。")


def session_variant(age: int, week_index: int, session_index: int) -> str:
    code = age_framework(age)["code"]
    labels = SESSION_VARIANTS.get(code, ["标准推进"])
    return labels[(week_index + session_index) % len(labels)]


def equipment_for_track(track: str) -> list[str]:
    return THEME_EQUIPMENT.get(track, ["标志桶", "训练垫", "饮水与记录板"])


def coach_cues_for_track(track: str) -> list[str]:
    return COACH_CUE_LIBRARY.get(track, ["先讲规则再开始", "动作质量优先于速度", "结束前做简短复盘"])


def rotated_phase_hints(track: str, phase_name: str, offset: int) -> list[str]:
    hints = TRACK_PHASE_EXERCISE_HINTS.get((track, phase_name), [])
    if not hints:
        return []
    step = offset % len(hints)
    return hints[step:] + hints[:step]


def exercise_progression(exercise: dict[str, Any], age: int, goal: str) -> dict[str, str]:
    category = exercise["category"]
    name = exercise["name"]
    presets = {
        "动物爬行接力": {
            "regression": "缩短距离到 8-10 米，采用单一爬行动作完成。",
            "standard": "完成熊爬、蟹步、青蛙跳三种动作轮换。",
            "progression": "加入方向变化或口令反应，提高节奏切换能力。",
            "target": "建立四点支撑稳定、肩髋协调和课堂参与感。",
        },
        "彩标反应跑": {
            "regression": "减少颜色指令数量，只做单方向启动。",
            "standard": "完成多颜色口令 + 单次变向触标。",
            "progression": "加入假动作或双重口令，提高反应抑制与变向效率。",
            "target": "提升反应、启动和快速变向能力。",
        },
        "跨栏协调跑": {
            "regression": "降低栏架高度，减少步频要求。",
            "standard": "完成高抬腿、并步、单脚快频三种过栏形式。",
            "progression": "加入计时或节拍要求，提高跑姿和步频稳定性。",
            "target": "改善跑姿节奏、摆臂和脚踝快速触地能力。",
        },
        "药球前抛与转体抛": {
            "regression": "使用更轻药球，减少转体幅度。",
            "standard": "完成前抛与转体抛各 3 组，强调全身协同。",
            "progression": "加入连续输出或跨步抛，提高爆发衔接。",
            "target": "建立髋膝踝协同蹬伸和躯干传力。",
        },
        "核心死虫与侧桥": {
            "regression": "缩短保持时间，先做手脚分离版本。",
            "standard": "完成死虫和侧桥标准版，保持呼吸与骨盆稳定。",
            "progression": "加入弹力带、抬腿或触碰任务，提高抗旋转能力。",
            "target": "提高腰盆稳定和呼吸控制能力。",
        },
        "折返跑节奏组": {
            "regression": "缩短折返距离，减少总组数。",
            "standard": "按固定距离和恢复完成节奏折返跑。",
            "progression": "加入配速目标或更复杂转身要求，提高专项耐力。",
            "target": "提升变向节奏、心肺负荷耐受和速度保持能力。",
        },
        "跳绳步频控制": {
            "regression": "采用无绳模拟或单摇短时段练习。",
            "standard": "完成单摇 + 步频切换，保持稳定节奏。",
            "progression": "加入双摇尝试、变速跳或组合步伐。",
            "target": "改善步频节奏、协调与有氧承受能力。",
        },
        "立定跳远技术分解": {
            "regression": "先分解摆臂和蹬伸，不要求完整远度输出。",
            "standard": "完成技术分解后做完整起跳与落地练习。",
            "progression": "加入连续跳或录像反馈，提高成绩转化。",
            "target": "提升起跳效率、摆臂衔接和落地稳定。",
        },
        "间歇跑配速练习": {
            "regression": "缩短跑段距离，降低目标配速要求。",
            "standard": "按固定距离和恢复完成配速控制。",
            "progression": "加入更严格配速区间或后程加速要求。",
            "target": "建立配速意识、呼吸节奏和耐力输出稳定性。",
        },
        "平衡垫单腿稳定": {
            "regression": "先在平地完成单腿站立和轻触点。",
            "standard": "在平衡垫上完成单腿站立与触点任务。",
            "progression": "加入抛接球或视线干扰，提高动态稳定。",
            "target": "提高单腿控制、骨盆稳定和踝膝对线。",
        },
        "趣味循环减脂站": {
            "regression": "缩短站点时间，减少轮数和复杂动作。",
            "standard": "完成 4-5 站循环，控制动作质量和节奏。",
            "progression": "加入更高密度轮转或更多复合动作。",
            "target": "提升总活动量、课堂心率和持续参与度。",
        },
        "放松拉伸与呼吸恢复": {
            "regression": "减少动作数量，重点做呼吸和小腿髋部放松。",
            "standard": "完成主要部位拉伸与呼吸回落。",
            "progression": "加入更精细的主动活动度控制和恢复指导。",
            "target": "促进恢复、降低紧张并帮助家长衔接课后管理。",
        },
    }
    fallback = {
        "regression": f"{name} 可先从更低动作难度、较短距离或较少次数开始。",
        "standard": f"{name} 采用标准处方执行，重点保证动作质量。",
        "progression": f"{name} 在动作稳定后逐步增加速度、次数或复杂度。",
        "target": f"{category} 能力作为本节课的关键训练输出。",
    }
    result = presets.get(name, fallback).copy()
    if age <= 6:
        result["level"] = "启蒙版"
    elif age <= 9:
        result["level"] = "基础版"
    elif age <= 12:
        result["level"] = "标准版"
    else:
        result["level"] = "进阶版"
    if goal == "体考专项提升":
        result["target"] = result["target"] + " 并服务于体考项目成绩转化。"
    elif goal == "跑步技术与耐力":
        result["target"] = result["target"] + " 并服务于跑姿效率与耐力稳定。"
    return result


def make_block(exercise: dict[str, Any], duration_min: int, intensity: str, coach_tip: str, framework: dict[str, Any], phase_name: str, age: int, goal: str) -> dict[str, Any]:
    progression = exercise_progression(exercise, age, goal)
    return {
        "phase": phase_name,
        "category": exercise["category"],
        "title": exercise["name"],
        "duration_min": duration_min,
        "duration_label": f"{duration_min} 分钟",
        "description": exercise["description"],
        "cues": exercise["cues"],
        "prescription": exercise["prescription"],
        "intensity": intensity,
        "sets_reps": exercise["prescription"],
        "rest": framework["rest"],
        "coach_tip": coach_tip,
        "safety": "动作优先于数量，如出现明显代偿或疲劳下降，立即降级处理。",
        "level_label": progression["level"],
        "regression": progression["regression"],
        "standard": progression["standard"],
        "progression": progression["progression"],
        "target_outcome": progression["target"],
        "videos": video_links(exercise["video_query"]),
    }


def phase_category_preferences(goal: str, framework: dict[str, Any], session_duration_min: int) -> list[list[str]]:
    goal_categories = GOAL_FRAMEWORKS.get(goal, {}).get("primary_categories", [])
    framework_categories = framework.get("priority_categories", [])
    common_warm = ["热身激活", "有氧协调", "姿态控制", "灵敏反应"]
    common_support = ["稳定控制", "姿态控制", "灵敏反应", "有氧协调"]
    common_main = goal_categories + framework_categories
    common_assist = ["稳定控制", "力量爆发", "姿态控制", "跑步技术", "体考专项"]
    common_conditioning = ["速度耐力", "跑步专项", "代谢循环", "有氧协调", "灵敏反应"]
    common_cooldown = ["整理放松"]
    if session_duration_min == 90:
        return [
            common_warm,
            goal_categories + common_support,
            common_main,
            common_assist + goal_categories,
            goal_categories + common_conditioning,
            common_cooldown,
        ]
    return [
        common_warm,
        goal_categories + common_support,
        common_main,
        goal_categories + common_conditioning,
        common_cooldown,
    ]


def phase_specific_preferences(phase_name: str, goal: str, framework: dict[str, Any], focus: str = "", track: str = "") -> list[str]:
    goal_categories = GOAL_FRAMEWORKS.get(goal, {}).get("primary_categories", [])
    framework_categories = framework.get("priority_categories", [])
    focus_categories = FOCUS_CATEGORY_MAP.get(focus, [])
    track_categories = {
        "森林探险": ["热身激活", "体考专项", "灵敏反应", "有氧协调"],
        "彩虹闯关": ["灵敏反应", "有氧协调", "姿态控制", "力量爆发"],
        "小勇士课堂": ["体考专项", "力量爆发", "稳定控制", "速度耐力"],
        "平衡星球": ["姿态控制", "稳定控制", "有氧协调", "整理放松"],
        "跑动主线": ["跑步技术", "跑步专项", "速度耐力", "有氧协调"],
        "跳跃主线": ["力量爆发", "体考专项", "灵敏反应", "姿态控制"],
        "投掷主线": ["体考专项", "力量爆发", "稳定控制", "姿态控制"],
        "支撑主线": ["稳定控制", "姿态控制", "跑步技术", "有氧协调"],
    }.get(track, [])
    mapping = {
        "趣味热身": ["热身激活", "灵敏反应", "有氧协调"],
        "基础动作": ["姿态控制", "稳定控制", "跑步技术", "热身激活"],
        "协调游戏": ["灵敏反应", "体考专项", "有氧协调", "力量爆发"],
        "轻力量": ["稳定控制", "力量爆发", "姿态控制"],
        "轻体能": ["有氧协调", "速度耐力", "代谢循环", "灵敏反应"],
        "动态热身": ["热身激活", "灵敏反应", "有氧协调"],
        "动作技术": ["跑步技术", "姿态控制", "稳定控制", "灵敏反应"],
        "主项能力": goal_categories + ["体考专项", "跑步技术", "力量爆发", "灵敏反应", "速度耐力"],
        "力量稳定": ["稳定控制", "姿态控制", "力量爆发"],
        "基础体能": ["速度耐力", "有氧协调", "代谢循环", "力量爆发"],
        "专项热身": ["热身激活", "跑步技术", "有氧协调", "灵敏反应"],
        "技术修正": ["跑步技术", "体考专项", "姿态控制", "稳定控制"],
        "技术打磨": ["体考专项", "跑步技术", "力量爆发", "稳定控制"],
        "主训练段": goal_categories + ["跑步专项", "体考专项", "速度耐力"],
        "主专项训练": goal_categories + ["体考专项", "跑步专项", "力量爆发"],
        "辅助能力": ["稳定控制", "力量爆发", "姿态控制", "灵敏反应"],
        "力量爆发": ["力量爆发", "稳定控制", "体考专项"],
        "体能补充": ["速度耐力", "跑步专项", "有氧协调", "代谢循环"],
        "体能强化": ["速度耐力", "跑步专项", "代谢循环", "力量爆发"],
        "放松整理": ["整理放松"],
        "恢复整理": ["整理放松"],
    }
    if phase_name == "主项能力":
        track_main_mapping = {
            "跑动主线": ["跑步专项", "跑步技术", "速度耐力", "有氧协调"],
            "跳跃主线": ["力量爆发", "体考专项", "灵敏反应", "有氧协调"],
            "投掷主线": ["体考专项", "力量爆发", "姿态控制", "稳定控制"],
            "支撑主线": ["稳定控制", "姿态控制", "跑步技术", "有氧协调"],
        }
        if track in track_main_mapping:
            return track_main_mapping[track] + focus_categories + track_categories
    if phase_name == "协调游戏":
        track_game_mapping = {
            "森林探险": ["体考专项", "灵敏反应", "有氧协调", "稳定控制"],
            "彩虹闯关": ["灵敏反应", "有氧协调", "力量爆发", "姿态控制"],
            "小勇士课堂": ["体考专项", "力量爆发", "灵敏反应", "速度耐力"],
            "平衡星球": ["姿态控制", "稳定控制", "有氧协调", "灵敏反应"],
        }
        if track in track_game_mapping:
            return track_game_mapping[track] + focus_categories + track_categories
    return focus_categories + track_categories + mapping.get(phase_name, goal_categories + framework_categories)


def session_exercise_pool(goal: str, age: int, focus: str, track: str, limit: int = 12) -> list[dict[str, Any]]:
    base = pick_exercises(goal, age, limit=limit)
    goal_categories = set(GOAL_FRAMEWORKS.get(goal, {}).get("primary_categories", []))
    focus_categories = set(FOCUS_CATEGORY_MAP.get(focus, []))
    track_hints = set(TRACK_EXERCISE_HINTS.get(track, []))
    extras = [
        item
        for item in EXERCISE_LIBRARY
        if item["age_min"] <= age <= item["age_max"]
        and (
            goal in item["goals"]
            or item["name"] in track_hints
            or item["category"] in focus_categories
            or item["category"] in goal_categories
        )
    ]
    pool: list[dict[str, Any]] = []
    for item in base + extras:
        if item not in pool:
            pool.append(item)
        if len(pool) >= limit:
            break
    return pool


def ordered_session_exercises(goal: str, age: int, session_duration_min: int, offset: int, focus: str) -> list[dict[str, Any]]:
    framework = age_framework(age)
    phase_names = framework["block_names_90"] if session_duration_min == 90 else framework["block_names_60"]
    track = theme_track(age, focus, offset)
    chosen = session_exercise_pool(goal, age, focus, track)
    preferences = [
        phase_specific_preferences(phase_name, goal, framework, focus, track) or base_preferences
        for phase_name, base_preferences in zip(
            phase_names,
            phase_category_preferences(goal, framework, session_duration_min),
        )
    ]
    counts: dict[str, int] = {}
    selected: list[dict[str, Any]] = []

    track_hints = TRACK_EXERCISE_HINTS.get(track, [])

    def score(exercise: dict[str, Any], categories: list[str], phase_index: int) -> tuple[int, int, int, int, int, int]:
        category = exercise["category"]
        phase_name = phase_names[phase_index]
        phase_track_hints = rotated_phase_hints(track, phase_name, offset)
        hint_rank = phase_track_hints.index(exercise["name"]) if exercise["name"] in phase_track_hints else 999
        category_rank = categories.index(category) if category in categories else len(categories) + 3
        usage_penalty = counts.get(exercise["name"], 0)
        goal_bonus = 0 if category in GOAL_FRAMEWORKS.get(goal, {}).get("primary_categories", []) else 1
        track_bonus = 0 if exercise["name"] in track_hints else 1
        phase_track_bonus = 0 if exercise["name"] in phase_track_hints else 1
        rotation_bonus = (chosen.index(exercise) - offset) % len(chosen)
        if phase_index == len(preferences) - 1 and category == "整理放松":
            category_rank = -2
        return (phase_track_bonus, hint_rank, category_rank, track_bonus, usage_penalty, goal_bonus, rotation_bonus)

    for phase_index, categories in enumerate(preferences):
        is_last_phase = phase_index == len(preferences) - 1
        phase_name = phase_names[phase_index]
        phase_track_hints = rotated_phase_hints(track, phase_name, offset)
        if is_last_phase:
            phase_candidates = [exercise for exercise in chosen if exercise["category"] == "整理放松"] or chosen
        else:
            phase_candidates = [exercise for exercise in chosen if exercise["category"] != "整理放松"] or chosen
        hinted_candidates = [exercise for exercise in phase_candidates if exercise["name"] in phase_track_hints]
        if hinted_candidates:
            phase_candidates = hinted_candidates + [exercise for exercise in phase_candidates if exercise["name"] not in phase_track_hints]
        unused = [exercise for exercise in phase_candidates if counts.get(exercise["name"], 0) == 0]
        pool = unused or phase_candidates
        best = min(pool, key=lambda exercise: score(exercise, categories, phase_index))
        counts[best["name"]] = counts.get(best["name"], 0) + 1
        selected.append(best)
    return selected


def rotate_session_blocks(goal: str, age: int, session_duration_min: int, offset: int, focus: str) -> list[dict[str, Any]]:
    framework = age_framework(age)
    pattern = framework["session_patterns"][session_duration_min]
    phase_names = framework["block_names_90"] if session_duration_min == 90 else framework["block_names_60"]
    track = theme_track(age, focus, offset)
    exercises = ordered_session_exercises(goal, age, session_duration_min, offset, focus)
    intensity_labels = (
        ["低", "低到中", "中到高", "中", "中到高", "低"]
        if session_duration_min == 90
        else ["低", "中", "中到高", "中到高", "低"]
    )
    coach_tips = [
        "先建立课堂秩序和身体状态，再进入正式训练。",
        "技术段强调动作标准和反馈，不用急着上强度。",
        f"主训练段围绕“{focus}”推进，以达成当前周期目标为核心。",
        "辅助段用于补短板、控姿态或提高专项支撑能力。",
        "体能段控制呼吸、节奏和完成质量，避免过度透支。",
        "放松段帮助恢复，也方便教练向家长复盘课堂状态。",
    ]
    if session_duration_min != 90:
        coach_tips = [coach_tips[0], coach_tips[1], coach_tips[2], coach_tips[4], coach_tips[5]]
    blocks = []
    elapsed = 0
    for exercise, minutes, intensity, tip, phase_name in zip(exercises, pattern, intensity_labels, coach_tips, phase_names):
        block = make_block(exercise, minutes, intensity, tip, framework, phase_name, age, goal)
        block["order"] = len(blocks) + 1
        block["start_min"] = elapsed
        block["end_min"] = elapsed + minutes
        block["time_range"] = f"{elapsed:02d}-{elapsed + minutes:02d} 分钟"
        block["theme_track"] = track
        elapsed += minutes
        blocks.append(block)
    return blocks


def build_session_templates(goal: str, age: int, session_duration_min: int, weekly_focus: list[str]) -> list[dict[str, Any]]:
    framework = age_framework(age)
    sessions = []
    for index, focus in enumerate(weekly_focus[:3], start=1):
        blocks = rotate_session_blocks(goal, age, session_duration_min, index - 1, focus)
        track = theme_track(age, focus, index - 1)
        variant = session_variant(age, 0, index - 1)
        sessions.append(
            {
                "session_name": f"标准课模版 {index}",
                "focus": focus,
                "theme_track": track,
                "session_variant": variant,
                "storyline": storyline_for_track(track, focus),
                "equipment": equipment_for_track(track),
                "coach_cues": coach_cues_for_track(track),
                "duration_min": session_duration_min,
                "duration_label": f"{session_duration_min} 分钟",
                "coach_brief": (
                    f"适配 {framework['label']}，围绕“{focus}”组织课程，"
                    f"本模版以“{variant}”为课次重点，"
                    f"从热身到主训练再到恢复收尾，时长完整覆盖 {session_duration_min} 分钟。"
                ),
                "blocks": blocks,
            }
        )
    return sessions


def build_weekly_plan(goal: str, age: int, weeks: int, frequency: int) -> list[dict[str, Any]]:
    chosen = pick_exercises(goal, age)
    weekly_focus = generate_cycle_focus(goal, weeks, age)
    plan = []
    for week_index in range(weeks):
        week_focus = weekly_focus[week_index]
        items = []
        for session_index in range(frequency):
            first = chosen[(week_index + session_index) % len(chosen)]
            second = chosen[(week_index + session_index + 1) % len(chosen)]
            items.append(
                {
                    "title": f"第 {week_index + 1} 周 / 第 {session_index + 1} 课",
                    "focus": week_focus,
                    "content": f"{first['name']} + {second['name']}",
                    "load": "RPE 5-7，动作质量优先，保留适度训练余量。",
                    "coach_note": "先保证技术，再逐步增加速度或次数。",
                }
            )
        plan.append({"week": week_index + 1, "focus": week_focus, "sessions": items})
    return plan


def build_weekly_plan_detailed(goal: str, age: int, weeks: int, frequency: int, session_duration_min: int) -> list[dict[str, Any]]:
    framework = age_framework(age)
    weekly_focus = generate_cycle_focus(goal, weeks, age)
    detailed = []
    for week_index in range(weeks):
        week_focus = weekly_focus[week_index]
        session_items = []
        for session_index in range(frequency):
            blocks = rotate_session_blocks(goal, age, session_duration_min, week_index + session_index, week_focus)
            track = theme_track(age, week_focus, week_index + session_index)
            variant = session_variant(age, week_index, session_index)
            session_items.append(
                {
                    "id": f"week-{week_index + 1}-session-{session_index + 1}",
                    "week": week_index + 1,
                    "session_no": session_index + 1,
                    "title": f"第 {week_index + 1} 周 / 第 {session_index + 1} 课",
                    "focus": week_focus,
                    "theme_track": track,
                    "session_variant": variant,
                    "storyline": storyline_for_track(track, week_focus),
                    "equipment": equipment_for_track(track),
                    "coach_cues": coach_cues_for_track(track),
                    "duration_min": session_duration_min,
                    "duration_label": f"{session_duration_min} 分钟",
                    "intensity_target": framework["intensity"],
                    "coach_summary": f"按“{' / '.join(framework['key_points'])}”推进，本节以“{variant}”为重点，先质量后负荷，确保适配 {framework['label']}。",
                    "blocks": blocks,
                }
            )
        detailed.append({"week": week_index + 1, "focus": week_focus, "sessions": session_items})
    return detailed


def athlete_profile_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now().isoformat(timespec="seconds")
    return {
        "id": payload.get("athlete_id") or uuid.uuid4().hex,
        "created_at": payload.get("created_at", now),
        "name": payload.get("name", "未命名学员").strip() or "未命名学员",
        "age": int(payload.get("age", 10) or 10),
        "trainee_group": payload.get("trainee_group", "青少年"),
        "gender": payload.get("gender", "未说明"),
        "height": payload.get("height", ""),
        "weight": payload.get("weight", ""),
        "school": payload.get("school", "").strip(),
        "grade": payload.get("grade", "").strip(),
        "guardian_name": payload.get("guardian_name", "").strip(),
        "guardian_phone": payload.get("guardian_phone", "").strip(),
        "training_experience": payload.get("training_experience", "").strip(),
        "sport_preference": payload.get("sport_preference", "").strip(),
        "available_schedule": payload.get("available_schedule", "").strip(),
        "medical_history": payload.get("medical_history", "").strip(),
        "injury_history": payload.get("injury_history", "").strip(),
        "baseline_metrics": payload.get("baseline_metrics", "").strip(),
        "personality_notes": payload.get("personality_notes", "").strip(),
        "training_type": payload.get("training_type", "私教课"),
        "training_goal": payload.get("training_goal", "青少年体适能启蒙"),
        "cycle_weeks": int(payload.get("cycle_weeks", 8) or 8),
        "sessions_per_week": int(payload.get("sessions_per_week", 2) or 2),
        "session_duration_min": int(payload.get("session_duration_min", 60) or 60),
        "assessment": payload.get("assessment", "").strip(),
        "needs": payload.get("needs", "").strip(),
        "constraints": payload.get("constraints", "").strip(),
        "updated_at": now,
    }


def save_athlete_profile(payload: dict[str, Any]) -> dict[str, Any]:
    ensure_dirs()
    profile = athlete_profile_from_payload(payload)
    if supabase_enabled():
        try:
            return save_athlete_profile_cloud(profile)
        except Exception as exc:
            print(f"Supabase athlete save failed, fallback to local storage: {exc}", file=sys.stderr)
    path = ATHLETE_DIR / f"{profile['id']}.json"
    path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    return profile


def delete_athlete_profile(athlete_id: str) -> dict[str, Any]:
    ensure_dirs()
    if supabase_enabled():
        try:
            return delete_athlete_profile_cloud(athlete_id)
        except Exception as exc:
            print(f"Supabase athlete delete failed, fallback to local storage: {exc}", file=sys.stderr)
    path = ATHLETE_DIR / f"{athlete_id}.json"
    profile: dict[str, Any] = {"id": athlete_id}
    if path.exists():
        try:
            profile = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            profile = {"id": athlete_id}
        path.unlink()

    files = sorted(REPORT_DIR.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    for report_path in files:
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        report_athlete = report.get("athlete", {})
        if report_athlete.get("id") != athlete_id:
            continue
        delete_media_items(report.get("media", []))
        report_path.unlink()
    return profile


def list_athlete_profiles(limit: int = 10) -> list[dict[str, Any]]:
    ensure_dirs()
    if supabase_enabled():
        try:
            return list_athlete_profiles_cloud(limit)
        except Exception as exc:
            print(f"Supabase athlete list failed, fallback to local storage: {exc}", file=sys.stderr)
    profiles = []
    files = sorted(ATHLETE_DIR.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    for path in files[:limit]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        profiles.append(
            {
                "id": data.get("id", ""),
                "name": data.get("name", "未命名学员"),
                "age": data.get("age", ""),
                "trainee_group": data.get("trainee_group", "青少年"),
                "gender": data.get("gender", ""),
                "guardian_phone": data.get("guardian_phone", ""),
                "goal": data.get("training_goal", ""),
                "training_type": data.get("training_type", ""),
                "session_duration_min": data.get("session_duration_min", 60),
                "updated_at": data.get("updated_at", ""),
                "profile": data,
            }
        )
    return profiles


def build_plan(payload: dict[str, Any]) -> dict[str, Any]:
    athlete = athlete_profile_from_payload(payload)
    framework = age_framework(athlete["age"])
    age = athlete["age"]
    goal = athlete["training_goal"]
    weeks = athlete["cycle_weeks"]
    frequency = athlete["sessions_per_week"]
    duration_min = athlete["session_duration_min"]
    weekly_focus = generate_cycle_focus(goal, weeks, age)
    emphasis = training_emphasis(goal)
    session_templates = build_session_templates(goal, age, duration_min, weekly_focus)
    weekly_plan = build_weekly_plan(goal, age, weeks, frequency)
    weekly_plan_detailed = build_weekly_plan_detailed(goal, age, weeks, frequency, duration_min)

    return {
        "athlete": {
            "id": athlete["id"],
            "name": athlete["name"],
            "age": age,
            "trainee_group": athlete["trainee_group"],
            "gender": athlete["gender"],
            "height": athlete["height"],
            "weight": athlete["weight"],
            "school": athlete["school"],
            "grade": athlete["grade"],
            "guardian_name": athlete["guardian_name"],
            "guardian_phone": athlete["guardian_phone"],
            "band": age_band(age),
            "age_framework": framework["label"],
            "goal": goal,
            "training_type": athlete["training_type"],
        },
        "summary": {
            "training_needs": athlete["needs"] or "提升基础体能与训练兴趣。",
            "assessment": athlete["assessment"] or "建议完成动作模式评估、柔韧性筛查和基础心肺测试。",
            "constraints": athlete["constraints"] or "暂无明确禁忌，训练中持续关注疲劳和动作代偿。",
            "training_background": athlete["training_experience"] or "暂无系统训练经历记录。",
            "health_notes": athlete["medical_history"] or athlete["injury_history"] or "暂无特殊病史与伤病说明。",
            "schedule_notes": athlete["available_schedule"] or "训练时间可与家长进一步确认。",
            "baseline_metrics": athlete["baseline_metrics"] or "建议首课完成基础测试并补录数据。",
            "periodisation_logic": f"本方案按 {framework['label']} 的发育特点设计，以 {'、'.join(framework['key_points'])} 为课堂主线。",
            "coach_takeaway": (
                f"{athlete['name']}处于{framework['label']}，当前优先方向是“{emphasis['main']}”，"
                f"辅助强化“{emphasis['support']}”，并通过周期推进逐步达成“{GOAL_FRAMEWORKS.get(goal, {}).get('coach_goal', '阶段训练目标')}”。"
            ),
        },
        "plan_overview": {
            "cycle_weeks": weeks,
            "sessions_per_week": frequency,
            "recommended_session_duration": f"{duration_min}分钟",
            "session_duration_min": duration_min,
            "framework_label": framework["label"],
            "framework_points": framework["key_points"],
            "parent_focus": "建议每 2 周向家长同步一次课堂出勤、动作完成度、训练感受和家庭练习执行情况。",
        },
        "weekly_plan": weekly_plan,
        "weekly_plan_detailed": weekly_plan_detailed,
        "session_templates": session_templates,
        "parent_report_template": {
            "title": f"{athlete['name']} 家长训练汇报",
            "tone": "专业、清晰、可直接转发家长群或私聊家长。",
            "headline": f"今天的课程完整覆盖 {duration_min} 分钟，重点围绕“{goal}”推进。",
            "highlights": [
                "本次课按照热身激活、动作技术、主训练段和恢复整理四个层级展开。",
                "教练重点记录训练参与度、动作规范度和课中反馈，便于家长理解真实进展。",
                "建议课后配合轻量家庭练习和睡眠补水，帮助下一次课程更稳定地衔接。",
            ],
            "homework": "每天做 1 组基础拉伸 + 1 组轻量协调练习，控制总时长 8-12 分钟即可。",
        },
    }


def recent_reports(limit: int = 6) -> list[dict[str, Any]]:
    ensure_dirs()
    if supabase_enabled():
        try:
            return recent_reports_cloud(limit)
        except Exception as exc:
            print(f"Supabase recent reports failed, fallback to local storage: {exc}", file=sys.stderr)
    files = sorted(REPORT_DIR.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    reports = []
    for path in files[:limit]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        reports.append(
            {
                "id": data.get("id", ""),
                "athlete_name": data.get("athlete", {}).get("name", "未命名学员"),
                "goal": data.get("plan", {}).get("athlete", {}).get("goal", ""),
                "date": data.get("session", {}).get("date", ""),
                "summary": data.get("parent_friendly", {}).get("headline", ""),
                "media_count": len(data.get("media", [])),
                "engagement": data.get("session", {}).get("engagement", ""),
            }
        )
    return reports


def delete_report(report_id: str) -> dict[str, Any]:
    ensure_dirs()
    if supabase_enabled():
        try:
            return delete_report_cloud(report_id)
        except Exception as exc:
            print(f"Supabase report delete failed, fallback to local storage: {exc}", file=sys.stderr)
    files = sorted(REPORT_DIR.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    for path in files:
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if report.get("id") != report_id:
            continue
        delete_media_items(report.get("media", []))
        path.unlink()
        return report
    raise ValueError("未找到对应的训练报告")


def athlete_report_history(athlete: dict[str, Any], limit: int = 6) -> list[dict[str, Any]]:
    ensure_dirs()
    if supabase_enabled():
        try:
            return athlete_report_history_cloud(athlete, limit)
        except Exception as exc:
            print(f"Supabase athlete history failed, fallback to local storage: {exc}", file=sys.stderr)
    athlete_id = athlete.get("id", "")
    athlete_name = athlete.get("name", "")
    history: list[dict[str, Any]] = []
    files = sorted(REPORT_DIR.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        report_athlete = data.get("athlete", {})
        same_athlete = (
            athlete_id
            and report_athlete.get("id") == athlete_id
            or athlete_name
            and report_athlete.get("name") == athlete_name
        )
        if not same_athlete:
            continue
        history.append(data)
        if len(history) >= limit:
            break
    return list(reversed(history))


def clamp_score(value: float, low: int = 45, high: int = 95) -> int:
    return max(low, min(high, round(value)))


def dimension_progress(athlete: dict[str, Any], session: dict[str, Any], history: list[dict[str, Any]]) -> dict[str, Any]:
    goal = athlete.get("goal") or athlete.get("training_goal", "青少年体适能启蒙")
    engagement_map = {"一般": 58, "良好": 72, "积极": 84, "非常投入": 90}
    engagement = session.get("engagement", "良好")
    rpe = int(str(session.get("rpe", "6") or "6").split("/")[0])
    base = engagement_map.get(engagement, 72)
    session_count = len(history) + 1
    consistency_bonus = min(8, session_count * 2)

    dimensions = {
        "动作规范": base + (2 if rpe <= 7 else -1) + consistency_bonus * 0.3,
        "体能表现": base + rpe * 1.8 + consistency_bonus * 0.4,
        "专注投入": base + consistency_bonus * 0.5,
        "协调控制": base + (3 if "协调" in goal or "启蒙" in goal else 1) + consistency_bonus * 0.3,
        "训练习惯": 64 + consistency_bonus + (4 if history else 0),
    }
    if "跑步" in goal:
        dimensions["耐力节奏"] = base + rpe * 1.6 + consistency_bonus * 0.4
    if "体考" in goal or "爆发" in goal:
        dimensions["速度爆发"] = base + rpe * 1.5 + consistency_bonus * 0.35
    if "姿态" in goal or "稳定" in goal:
        dimensions["姿态稳定"] = base + 4 + consistency_bonus * 0.35

    current = {label: clamp_score(value) for label, value in dimensions.items()}
    previous = history[-1].get("parent_friendly", {}).get("progress_chart", {}).get("dimensions", []) if history else []
    previous_map = {item.get("label"): item.get("score", 0) for item in previous}
    previous_overall = history[-1].get("parent_friendly", {}).get("progress_chart", {}).get("overall_score", max(50, base - 4)) if history else max(50, base - 4)
    chart_dimensions = []
    for label, score in current.items():
        prev_score = previous_map.get(label, max(50, score - 4))
        delta = score - prev_score
        chart_dimensions.append(
            {
                "label": label,
                "score": score,
                "delta": delta,
                "status": "提升中" if delta >= 3 else "保持稳定" if delta >= 0 else "需巩固",
            }
        )

    trend = []
    recent = history[-4:] if history else []
    for item in recent:
        trend.append(
            {
                "label": item.get("session", {}).get("date", "") or item.get("created_at", "")[:10],
                "score": item.get("parent_friendly", {}).get("progress_chart", {}).get("overall_score", 68),
            }
        )
    overall_score = round(sum(item["score"] for item in chart_dimensions) / len(chart_dimensions))
    trend.append({"label": session.get("date", "本次"), "score": overall_score})
    weekly_delta = overall_score - previous_overall
    goal_completion = clamp_score(overall_score + (4 if session_count >= 3 else 0), 50, 98)
    return {
        "overall_score": overall_score,
        "weekly_delta": weekly_delta,
        "goal_completion": goal_completion,
        "dimensions": chart_dimensions,
        "trend": trend,
    }


def report_progress_linkage(plan: dict[str, Any], history: list[dict[str, Any]]) -> dict[str, str]:
    weekly_plan = plan.get("weekly_plan_detailed", [])
    session_index = len(history)
    if not weekly_plan:
        return {
            "current_track_progress": "本周继续围绕既定主线推进，当前课堂表现保持稳定。",
            "next_session_bridge": "下节课会在当前基础上继续巩固动作质量并逐步增加训练挑战。",
        }
    flat_sessions = [session for week in weekly_plan for session in week.get("sessions", [])]
    current_session = flat_sessions[min(session_index, len(flat_sessions) - 1)]
    next_session = flat_sessions[min(session_index + 1, len(flat_sessions) - 1)] if flat_sessions else current_session
    current_track = current_session.get("theme_track", current_session.get("focus", "本周主线"))
    current_focus = current_session.get("focus", "当前重点")
    next_track = next_session.get("theme_track", next_session.get("focus", "下节主线"))
    next_focus = next_session.get("focus", "下节重点")
    return {
        "current_track_progress": f"本周主线为“{current_track}”，当前重点围绕“{current_focus}”推进，课堂表现正在向该方向稳定积累。",
        "next_session_bridge": f"下节课将衔接到“{next_track}”，继续围绕“{next_focus}”做进阶练习，帮助学员把本次课堂成果延续到下一次训练。",
    }


def decode_data_url(item: dict[str, Any], athlete_name: str, index: int) -> dict[str, Any]:
    if supabase_enabled():
        try:
            return upload_media_to_supabase(item, athlete_name, index)
        except Exception as exc:
            print(f"Supabase media upload failed, fallback to local storage: {exc}", file=sys.stderr)
    raw = item.get("data_url", "")
    match = re.match(r"data:(.*?);base64,(.*)", raw)
    if not match:
        raise ValueError("媒体数据格式不正确")
    mime_type, encoded = match.groups()
    extension = mimetypes.guess_extension(mime_type) or (".bin" if "/" not in mime_type else f".{mime_type.split('/')[-1]}")
    filename = f"{sanitize_filename(athlete_name)}-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{index}{extension}"
    target = MEDIA_DIR / filename
    target.write_bytes(base64.b64decode(encoded))
    return {
        "name": item.get("name", filename),
        "mime_type": mime_type,
        "url": f"/media/{quote(filename)}",
        "kind": "video" if mime_type.startswith("video/") else "image",
    }


def build_parent_friendly_report(athlete: dict[str, Any], session: dict[str, Any], media: list[dict[str, Any]], history: list[dict[str, Any]], plan: dict[str, Any]) -> dict[str, Any]:
    athlete_name = athlete.get("name", "学员")
    engagement = session.get("engagement", "良好")
    rpe = session.get("rpe", "6")
    progress_chart = dimension_progress(athlete, session, history)
    linkage = report_progress_linkage(plan, history)
    headline = f"{athlete_name} 今天完成了一节 {session.get('duration', '60分钟')} 训练课，课堂投入度为“{engagement}”。"
    return {
        "headline": headline,
        "intro": f"本次课程主要围绕 {session.get('content', '既定训练内容')} 展开，课堂主观强度约为 {rpe}/10。",
        "coach_observation": session.get("coach_notes", "") or "整体配合良好，建议继续保持训练节奏。",
        "parent_actions": [
            "今晚注意补水和睡眠，帮助身体恢复。",
            f"家庭练习建议：{session.get('homework', '完成基础拉伸和轻量协调练习。')}",
            "如孩子反馈局部酸胀，可做轻柔放松，不建议额外加量。",
        ],
        "tags": [
            f"投入度 {engagement}",
            f"主观强度 {rpe}/10",
            f"素材 {len(media)} 个",
            f"综合进展 {progress_chart['overall_score']} 分",
        ],
        "progress_summary": f"从最近训练记录看，当前整体进展约为 {progress_chart['overall_score']} 分，建议持续保持出勤与家庭练习配合。",
        "progress_chart": progress_chart,
        "current_track_progress": linkage["current_track_progress"],
        "next_session_bridge": linkage["next_session_bridge"],
    }


def save_report(payload: dict[str, Any]) -> dict[str, Any]:
    ensure_dirs()
    athlete = payload.get("athlete", {})
    session = payload.get("session", {})
    plan = payload.get("plan", {})
    athlete_name = athlete.get("name", "未命名学员")
    media_items = payload.get("media", [])
    saved_media = [decode_data_url(item, athlete_name, index) for index, item in enumerate(media_items, start=1)]
    history = athlete_report_history(athlete)
    parent_friendly = build_parent_friendly_report(athlete, session, saved_media, history, plan)
    summary = (
        f"{athlete_name} 于 {session.get('date', '今日')} 完成 {session.get('duration', '60分钟')} 训练，"
        f"课堂表现 {session.get('engagement', '良好')}，主观强度 {session.get('rpe', '6')}/10。"
    )
    report = {
        "id": uuid.uuid4().hex,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "athlete": athlete,
        "plan": plan,
        "session": session,
        "media": saved_media,
        "parent_summary": summary + (session.get("coach_notes", "") or ""),
        "parent_friendly": parent_friendly,
    }
    if supabase_enabled():
        try:
            supabase_request(
                "POST",
                "/rest/v1/reports",
                query={"on_conflict": "id"},
                json_body=report_to_db_row(report),
                extra_headers={"Prefer": "resolution=merge-duplicates,return=representation"},
            )
            return report
        except Exception as exc:
            print(f"Supabase report save failed, fallback to local storage: {exc}", file=sys.stderr)
    filename = f"{sanitize_filename(athlete_name)}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    path = REPORT_DIR / filename
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def index_html() -> bytes:
    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>青少年训练课件与报告平台</title>
  <link rel="stylesheet" href="/static/styles.css" />
</head>
<body>
  <main class="page">
    <section class="auth-bar panel">
      <div class="auth-bar-copy">
        <p class="section-tag">Access Control</p>
        <strong>教练账号与权限管理</strong>
      </div>
      <div class="auth-user">
        <div>
          <span id="auth-role-pill" class="status-pill">未登录</span>
          <p id="auth-user-text">请先登录后再使用教练工作台。</p>
        </div>
        <button id="logout-btn" class="ghost" type="button" hidden>退出登录</button>
      </div>
    </section>

    <section class="hero">
      <div class="hero-copy">
        <p class="hero-kicker">神兽体育青少年训练系统</p>
        <h1>神兽体育青少年体适能训练会员课件系统与报告平台</h1>
        <p class="subtitle">覆盖幼儿、青少年与成人三类训练对象，支持真实教练课模版、60/90 分钟课次编排、学员档案管理和家长图文报告输出，适配早教、私教课、小班课/团课、专项（闯关）训练与跑步训练场景。</p>
      </div>
      <div class="hero-card">
        <span>适用场景</span>
        <strong>建档 / 排课 / 带课 / 复盘 / 家长沟通</strong>
        <p>支持周期训练计划、动作要求、示范视频入口、学员档案列表、训练照片短视频归档和家长版课后图文汇报。</p>
      </div>
    </section>

    <section class="dashboard-strip">
      <div class="metric-card"><span>训练对象</span><strong>幼儿 / 青少年 / 成人</strong></div>
      <div class="metric-card"><span>课时档位</span><strong>60 / 90 分钟</strong></div>
      <div class="metric-card"><span>核心模块</span><strong>档案 / 出课 / 报告</strong></div>
      <div class="metric-card"><span>输出对象</span><strong>教练与家长</strong></div>
    </section>

    <section class="workspace archive-layout">
      <section class="panel archive-panel">
        <div class="panel-head archive-head">
          <div class="archive-head-copy">
            <p class="section-tag">Athlete Library</p>
            <h2>学员档案列表</h2>
          </div>
        </div>
        <div class="archive-cta-row">
          <button id="new-athlete-btn" class="ghost accent-ghost archive-create-btn" type="button">新建学员</button>
        </div>
        <label class="field archive-search">
          <span>搜索会员</span>
          <input id="athlete-search" type="text" placeholder="输入会员姓名或家长手机号" />
        </label>
        <div id="athlete-list" class="athlete-list"></div>
      </section>

      <section class="panel form-panel">
        <div class="panel-head">
          <div>
            <p class="section-tag">Profile Builder</p>
            <h2>学员建档与课程设定</h2>
          </div>
          <div class="head-actions">
            <button id="sample-btn" class="ghost" type="button">填入示例</button>
            <button id="save-profile-btn" class="ghost accent-ghost" type="button">保存档案</button>
          </div>
        </div>
        <form id="plan-form" class="form-grid form-grid-horizontal">
          <label class="field"><span>学员姓名</span><input id="name" required placeholder="例如：李梓睿" /></label>
          <label class="field"><span>训练对象</span><select id="trainee-group"></select></label>
          <label class="field"><span>年龄</span><input id="age" type="number" min="3" max="60" value="10" required /></label>
          <label class="field"><span>性别</span>
            <select id="gender">
              <option value="男">男</option>
              <option value="女">女</option>
              <option value="未说明">未说明</option>
            </select>
          </label>
          <label class="field"><span>课程类型</span><select id="training-type"></select></label>
          <label class="field"><span>学校</span><input id="school" placeholder="例如：实验小学" /></label>
          <label class="field"><span>年级</span><input id="grade" placeholder="例如：四年级" /></label>
          <label class="field"><span>身高(cm)</span><input id="height" type="number" placeholder="可选" /></label>
          <label class="field"><span>体重(kg)</span><input id="weight" type="number" placeholder="可选" /></label>
          <label class="field"><span>家长姓名</span><input id="guardian-name" placeholder="例如：李女士" /></label>
          <label class="field"><span>家长电话</span><input id="guardian-phone" placeholder="例如：13800000000" /></label>
          <label class="field"><span>训练周期</span><select id="cycle-weeks"></select></label>
          <label class="field"><span>每周课次</span><select id="sessions-per-week"></select></label>
          <label class="field field-span-2"><span>训练目标</span><select id="training-goal"></select></label>
          <label class="field field-span-2"><span>单次课时</span><select id="session-duration"></select></label>
          <label class="field field-span-2"><span>既往训练经历</span><textarea id="training-experience" placeholder="例如：学过篮球 1 年，偶尔参加校队训练"></textarea></label>
          <label class="field field-span-2"><span>运动兴趣 / 偏好项目</span><textarea id="sport-preference" placeholder="例如：喜欢跑步、跳绳，不喜欢对抗性项目"></textarea></label>
          <label class="field field-span-2"><span>可训练时间安排</span><textarea id="available-schedule" placeholder="例如：周二、周四晚 7 点后，周六上午可安排"></textarea></label>
          <label class="field field-span-2"><span>当前评估情况</span><textarea id="assessment" placeholder="例如：核心控制一般、踝背屈受限、800米后程掉速明显"></textarea></label>
          <label class="field field-span-2"><span>基础测试数据</span><textarea id="baseline-metrics" placeholder="例如：50米 9.1 秒，立定跳远 156 cm，坐位体前屈 8 cm"></textarea></label>
          <label class="field field-span-2"><span>客户需求</span><textarea id="needs" placeholder="例如：暑假提升体考成绩，希望同时改善跑姿与耐力"></textarea></label>
          <label class="field field-span-2"><span>病史 / 医疗注意事项</span><textarea id="medical-history" placeholder="例如：有轻微哮喘史，剧烈运动前需充分热身"></textarea></label>
          <label class="field field-span-2"><span>既往伤病记录</span><textarea id="injury-history" placeholder="例如：半年前右踝扭伤，目前无明显疼痛"></textarea></label>
          <label class="field field-span-2"><span>注意事项 / 运动限制</span><textarea id="constraints" placeholder="例如：轻微扁平足、右膝偶发不适，需要控制跳跃量"></textarea></label>
          <label class="field field-span-2"><span>性格与课堂沟通备注</span><textarea id="personality-notes" placeholder="例如：慢热型，需要更多鼓励；对竞赛小游戏反应积极"></textarea></label>
          <button id="generate-btn" class="primary submit-btn" type="submit">生成定制训练课件</button>
        </form>
      </section>
    </section>

    <section class="panel output-panel">
      <div class="panel-head">
        <div>
          <p class="section-tag">Coach Output</p>
          <h2>训练计划与课程教案</h2>
        </div>
        <span id="status-pill" class="status-pill">等待生成</span>
      </div>
      <div id="empty-state" class="empty-state">完成建档后，这里会生成周期计划、60/90 分钟课程模板、动作要求和家长沟通模板。</div>
      <div id="plan-output" class="plan-output hidden">
        <section class="summary-grid" id="summary-grid"></section>
        <section class="plan-focus-board">
          <section class="plan-block">
            <div class="block-head"><h3>周期安排</h3><span>按周查看训练重点</span></div>
            <div id="weekly-plan" class="weekly-plan"></div>
          </section>
          <section class="plan-block">
            <div class="block-head"><h3>单节课教案</h3><span>点击每周课次即可查看和打印</span></div>
            <div id="lesson-detail" class="lesson-detail empty-state">从上方每周计划中选择一节课，这里会显示完整训练内容。</div>
          </section>
        </section>
        <section class="plan-block">
          <div class="block-head"><h3>课程模板</h3><span>完整覆盖单次课时</span></div>
          <div id="session-templates" class="session-templates"></div>
        </section>
        <section class="plan-block">
          <div class="block-head"><h3>家长沟通模板</h3><span>适合课后快速复盘</span></div>
          <div id="parent-template" class="parent-template"></div>
        </section>
      </div>
    </section>

    <section class="workspace secondary">
      <section class="panel report-panel">
        <div class="panel-head">
          <div>
            <p class="section-tag">Session Report</p>
            <h2>单次训练记录</h2>
          </div>
        </div>
        <form id="report-form" class="form-grid">
          <label class="field"><span>训练日期</span><input id="session-date" type="date" required /></label>
          <label class="field"><span>课次时长</span><select id="report-duration"></select></label>
          <label class="field"><span>课堂投入度</span>
            <select id="engagement">
              <option value="优秀">优秀</option>
              <option value="良好">良好</option>
              <option value="一般">一般</option>
              <option value="需激励">需激励</option>
            </select>
          </label>
          <label class="field"><span>主观强度 RPE</span><input id="rpe" type="number" min="1" max="10" value="6" /></label>
          <label class="field field-span-2"><span>本次完成内容</span><textarea id="session-content" placeholder="例如：热身激活、跨栏跑、折返跑、核心训练、拉伸恢复"></textarea></label>
          <label class="field field-span-2"><span>教练备注</span><textarea id="coach-notes" placeholder="例如：起跑反应更积极，但变向时重心还可以更低"></textarea></label>
          <label class="field field-span-2"><span>家庭练习建议</span><textarea id="homework" placeholder="例如：每天完成 2 组靠墙摆臂练习和 5 分钟踝髋拉伸"></textarea></label>
          <label class="field field-span-2"><span>上传训练照片 / 短视频</span><input id="media-files" type="file" accept="image/*,video/*" multiple /></label>
          <button id="save-report-btn" class="primary submit-btn" type="submit">保存本次训练报告</button>
        </form>
        <div id="save-message" class="save-message hidden"></div>
      </section>

      <section class="panel parent-preview-panel">
        <div class="panel-head">
          <div>
            <p class="section-tag">Parent Report</p>
            <h2>家长图文版预览</h2>
          </div>
        </div>
        <div id="parent-report-preview" class="parent-report-preview">
          <div class="empty-state">保存一次训练报告后，这里会生成更适合发给家长的图文版汇报。</div>
        </div>
      </section>
    </section>

    <section class="panel recent-panel">
      <div class="panel-head">
        <div>
          <p class="section-tag">Recent Reports</p>
          <h2>最近训练汇报</h2>
        </div>
      </div>
      <div id="recent-reports" class="recent-reports"></div>
    </section>
  </main>

  <div id="auth-gate" class="auth-gate active">
    <div class="auth-card">
      <p class="section-tag">Coach Login</p>
      <h2>登录神兽体育教练工作台</h2>
      <p class="auth-intro">系统现支持“管理员”和“教练”两类账号。管理员可删除学员与报告，教练可进行建档、排课、带课与课后记录。</p>
      <form id="login-form" class="auth-form">
        <label class="field"><span>账号</span><input id="login-username" autocomplete="username" placeholder="请输入账号" /></label>
        <label class="field"><span>密码</span><input id="login-password" type="password" autocomplete="current-password" placeholder="请输入密码" /></label>
        <button id="login-btn" class="primary" type="submit">登录进入系统</button>
      </form>
      <div id="auth-message" class="auth-message">未登录时，系统不会加载学员和训练数据。</div>
      <div class="auth-tip-grid">
        <article>
          <strong>管理员</strong>
          <p>可删除学员档案、训练报告和关联素材，适合店长或负责人。</p>
        </article>
        <article>
          <strong>教练</strong>
          <p>可正常建档、排课、记录训练和生成家长报告，但不能做高风险删除操作。</p>
        </article>
      </div>
    </div>
  </div>

  <script src="/static/app.js"></script>
</body>
</html>
"""
    return html.encode("utf-8")


def iter_watch_files() -> list[Path]:
    files: list[Path] = []
    for pattern in ("*.py", "static/*.js", "static/*.css"):
        files.extend(BASE_DIR.glob(pattern))
    return sorted(path for path in files if path.is_file())


def snapshot_mtimes() -> dict[Path, float]:
    return {path: path.stat().st_mtime for path in iter_watch_files()}


def run_with_reloader() -> None:
    child: subprocess.Popen[str] | None = None
    try:
        while True:
            env = os.environ.copy()
            env[RELOAD_ENV] = "1"
            child = subprocess.Popen([sys.executable, str(Path(__file__).name)], cwd=BASE_DIR, env=env)
            known_mtimes = snapshot_mtimes()

            while True:
                exit_code = child.poll()
                if exit_code is not None:
                    raise SystemExit(exit_code)

                time.sleep(1)
                current_mtimes = snapshot_mtimes()
                if current_mtimes != known_mtimes:
                    print("Detected file change, restarting server...")
                    child.send_signal(signal.SIGINT)
                    child.wait(timeout=5)
                    break
    except KeyboardInterrupt:
        if child and child.poll() is None:
            child.send_signal(signal.SIGINT)
            child.wait(timeout=5)


class AppHandler(BaseHTTPRequestHandler):
    def current_identity(self) -> dict[str, Any] | None:
        return current_identity_from_headers(self.headers)

    def require_identity(self) -> dict[str, Any] | None:
        identity = self.current_identity()
        if identity:
            return identity
        self.respond_json({"error": "请先登录后再继续操作", "auth_required": True}, status=401)
        return None

    def require_admin(self) -> dict[str, Any] | None:
        identity = self.require_identity()
        if not identity:
            return None
        if identity.get("role") == "admin":
            return identity
        self.respond_json({"error": "当前操作仅管理员可用", "forbidden": True}, status=403)
        return None

    def do_HEAD(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.respond(b"", "text/html; charset=utf-8")
            return
        if parsed.path.startswith("/static/"):
            self.respond(b"", self.static_content_type(parsed.path))
            return
        if parsed.path.startswith("/api/"):
            self.respond(b"", "application/json; charset=utf-8")
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_GET(self) -> None:
        ensure_dirs()
        parsed = urlparse(self.path)

        if parsed.path == "/":
            self.respond(index_html(), "text/html; charset=utf-8")
            return

        if parsed.path == "/api/auth-status":
            identity = self.current_identity()
            self.respond_json(
                {
                    "authenticated": bool(identity),
                    "user": auth_identity_payload(identity) if identity else None,
                }
            )
            return

        if parsed.path == "/api/bootstrap":
            identity = self.require_identity()
            if not identity:
                return
            self.respond_json(
                {
                    **BOOTSTRAP_DATA,
                    "recent_reports": recent_reports(),
                    "athlete_profiles": list_athlete_profiles(),
                    "auth": {"authenticated": True, "user": auth_identity_payload(identity)},
                }
            )
            return

        if parsed.path.startswith("/media/"):
            identity = self.require_identity()
            if not identity:
                return
            filename = unquote(parsed.path.removeprefix("/media/"))
            target = MEDIA_DIR / filename
            if not target.exists():
                self.send_error(HTTPStatus.NOT_FOUND, "Media not found")
                return
            mime_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            self.respond(target.read_bytes(), mime_type)
            return

        if parsed.path.startswith("/static/"):
            filename = parsed.path.removeprefix("/static/")
            try:
                self.respond(read_static_file(filename), self.static_content_type(parsed.path))
            except FileNotFoundError:
                self.send_error(HTTPStatus.NOT_FOUND, "Static file not found")
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        ensure_dirs()
        parsed = urlparse(self.path)
        payload = self.read_json()

        if parsed.path == "/api/login":
            username = str(payload.get("username", "")).strip()
            password = str(payload.get("password", "")).strip()
            user = authenticate_user(username, password)
            if not user:
                self.respond_json({"error": "账号或密码不正确"}, status=401)
                return
            token = create_session(user)
            self.respond_json(
                {"message": "登录成功", "user": auth_identity_payload(user)},
                extra_headers={"Set-Cookie": session_cookie(token)},
            )
            return

        if parsed.path == "/api/logout":
            cookie = parse_cookie_header(self.headers.get("Cookie"))
            token = cookie.get(SESSION_COOKIE_NAME)
            if token:
                SESSION_STORE.pop(token.value, None)
            self.respond_json({"message": "已退出登录"}, extra_headers={"Set-Cookie": clear_session_cookie()})
            return

        identity = self.require_identity()
        if not identity:
            return

        if parsed.path == "/api/save-athlete-profile":
            profile = save_athlete_profile(payload)
            self.respond_json({"message": "学员档案已保存", "profile": profile, "athlete_profiles": list_athlete_profiles()})
            return

        if parsed.path == "/api/delete-athlete-profile":
            if not self.require_admin():
                return
            athlete_id = str(payload.get("id", "")).strip()
            if not athlete_id:
                self.respond_json({"error": "缺少学员 ID"}, status=400)
                return
            try:
                profile = delete_athlete_profile(athlete_id)
            except ValueError as exc:
                self.respond_json({"error": str(exc)}, status=404)
                return
            self.respond_json(
                {
                    "message": f"{profile.get('name', '该学员')} 档案已删除",
                    "deleted_id": athlete_id,
                    "athlete_profiles": list_athlete_profiles(),
                    "recent_reports": recent_reports(),
                }
            )
            return

        if parsed.path == "/api/generate-plan":
            self.respond_json(build_plan(payload))
            return

        if parsed.path == "/api/save-session-report":
            try:
                report = save_report(payload)
            except ValueError as exc:
                self.respond_json({"error": str(exc)}, status=400)
                return
            self.respond_json(
                {
                    "message": "训练报告已保存",
                    "report": report,
                    "recent_reports": recent_reports(),
                    "athlete_profiles": list_athlete_profiles(),
                }
            )
            return

        if parsed.path == "/api/delete-session-report":
            if not self.require_admin():
                return
            report_id = str(payload.get("id", "")).strip()
            if not report_id:
                self.respond_json({"error": "缺少报告 ID"}, status=400)
                return
            try:
                report = delete_report(report_id)
            except ValueError as exc:
                self.respond_json({"error": str(exc)}, status=404)
                return
            self.respond_json(
                {
                    "message": f"{report.get('athlete', {}).get('name', '该学员')} 的训练报告已删除",
                    "deleted_id": report_id,
                    "recent_reports": recent_reports(),
                    "athlete_profiles": list_athlete_profiles(),
                }
            )
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        return json.loads(raw or "{}")

    def static_content_type(self, path: str) -> str:
        if path.endswith(".css"):
            return "text/css; charset=utf-8"
        if path.endswith(".js"):
            return "application/javascript; charset=utf-8"
        return "text/plain; charset=utf-8"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def respond(self, body: bytes, content_type: str, status: int = 200, extra_headers: dict[str, str] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if extra_headers:
            for key, value in extra_headers.items():
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def respond_json(self, payload: dict[str, Any], status: int = 200, extra_headers: dict[str, str] | None = None) -> None:
        self.respond(json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", status, extra_headers=extra_headers)


def main() -> None:
    ensure_dirs()
    host = os.environ.get(HOST_ENV, "127.0.0.1")
    port = int(os.environ.get(PORT_ENV, str(PORT)))
    reload_enabled = os.environ.get(ENABLE_RELOAD_ENV, "1") == "1"

    if reload_enabled and os.environ.get(RELOAD_ENV) != "1":
        print("Auto-reload enabled. Watching app and static files for changes.")
        run_with_reloader()
        return

    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"Server running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
