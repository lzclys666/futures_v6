#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stub
因子: 待定义 = stub

公式: 数据采集（无独立计算公式）

当前状态: ⚠️待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
import os
from pathlib import Path

ROOT = Path(r"D:\futures_v6\macro_engine\crawlers")
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

# ============================================================
# 每个品种的定义
# ============================================================
SPECIES = {
    "BU": {
        "name": "沥青",
        "exchange": "SHFE",
        "tier1": [
            ("BU_FUT_CLOSE",         "Brent原油期货价格",        "L4", "L1已由BR品种采集"),
            ("BU_STK_WARRANT",       "上期所沥青仓单",            "L4", "SHFE官网接口404"),
            ("BU_POS_NET",           "上期所前20净持仓",          "L4", "SHFE官网接口404"),
            ("BU_SPD_BASIS",         "沥青期现基差",              "L4", "华东沥青现货需隆众付费"),
            ("BU_SPT_EAST_CHINA",    "华东沥青现货价格",          "L4", "付费订阅: 隆众资讯"),
            ("BU_FX_USDCNY",         "美元兑人民币汇率",          "L4", "L1已由其他品种采集"),
            ("BU_STK_SOCIAL",        "沥青社会库存",              "L4", "付费订阅: 隆众资讯"),
        ],
        "tier2": [
            ("BU_STK_REFINE_RATE",   "沥青炼厂开工率",            "L4", "付费订阅: 隆众资讯"),
            ("BU_SPD_BU_BRENT",      "沥青-原油价比",             "L4", "BU品种待开发"),
            ("BU_MACRO_HIGHWAY",     "公路建设投资完成额",         "L4", "交通运输部月度数据"),
        ],
    },
    "EG": {
        "name": "乙二醇",
        "exchange": "DCE",
        "tier1": [
            ("EG_FUT_CLOSE",         "乙烯CFR东北亚价格",         "L4", "ICIS/隆众付费"),
            ("EG_STK_WARRANT",       "大商所乙二醇仓单",           "L4", "DCE接口待验证"),
            ("EG_POS_NET",           "大商所前20净持仓",           "L4", "DCE接口待验证"),
            ("EG_SPD_BASIS",         "乙二醇期现基差",             "L4", "华东出罐价需CCF付费"),
            ("EG_STK_PORT",          "乙二醇港口库存(华东)",       "L4", "付费订阅: CCF/隆众"),
            ("EG_STK_POLYESTER",     "聚酯涤纶长丝开工率",         "L4", "付费订阅: CCF"),
        ],
        "tier2": [
            ("EG_SPT_NAPTHA",        "石脑油CFR日本价格",          "L4", "AKShare接口待验证"),
            ("EG_STK_PLANT_RATE",    "乙二醇装置开工率",           "L4", "付费订阅: CCF"),
            ("EG_STK_COAL_RATE",     "煤制EG装置开工率",           "L4", "付费订阅: 隆众资讯"),
        ],
    },
    "J": {
        "name": "焦炭",
        "exchange": "DCE",
        "tier1": [
            ("J_SPT_MYSTEEEL",       "Mysteel焦炭现货价格",       "L4", "Mysteel付费"),
            ("J_STK_WARRANT",        "大商所焦炭仓单",             "L4", "DCE接口待验证"),
            ("J_POS_NET",            "大商所前20净持仓",           "L4", "DCE接口待验证"),
            ("J_SPD_BASIS",          "焦炭期现基差",               "L4", "Mysteel焦炭现货需付费"),
            ("J_SPD_NEAR_FAR",       "焦炭近远月价差",             "L4", "AKShare接口待验证"),
            ("J_SPT_CCI",            "焦煤价格(CCI)",              "L4", "汾渭/AKShare待验证"),
        ],
        "tier2": [
            ("J_FOB_EXPORT",         "焦炭出口价格(FOB)",         "L4", "汾渭/海关总署"),
            ("J_SPD_J_JM",           "焦炭/焦煤价比",              "L4", "J品种待开发"),
            ("J_STK_COKE_RATE",      "独立焦化厂开工率",           "L4", "付费订阅: 汾渭能源"),
            ("J_STK_STEEL_DAYS",    "样本钢厂焦炭库存可用天数",   "L4", "付费订阅: Mysteel"),
        ],
    },
    "PP": {
        "name": "聚丙烯",
        "exchange": "DCE",
        "tier1": [
            ("PP_STK_WARRANT",        "大商所聚丙烯仓单",           "L4", "DCE接口待验证"),
            ("PP_POS_NET",            "大商所前20净持仓",           "L4", "DCE接口待验证"),
            ("PP_SPD_BASIS",          "PP期现基差",                 "L4", "华东拉丝PP均价需隆众付费"),
            ("PP_SPT_CFR_CHINA",      "丙烯CFR中国价格",            "L4", "付费订阅: 隆众资讯(必配)"),
            ("PP_STK_PLANT_RATE",    "PP装置开工率",               "L4", "付费订阅: 隆众资讯"),
            ("PP_SPD_LAM_Copoly",   "PP拉丝-共聚价差",            "L4", "付费订阅: 隆众资讯"),
        ],
        "tier2": [
            ("PP_STK_PORT",           "PP港口库存",                 "L4", "付费订阅: 隆众资讯"),
            ("PP_STK_BAG_RATE",       "塑编开工率",                 "L4", "付费订阅: 卓创资讯"),
            ("PP_SPD_LLDPE_PP",      "PE-PP价差",                  "L4", "AKShare接口待验证"),
        ],
    },
    "Y": {
        "name": "豆油",
        "exchange": "DCE",
        "tier1": [
            ("Y_FUT_CBOT_SOY",       "CBOT大豆期货主力",           "L4", "AKShare接口待验证"),
            ("Y_FUT_CBOT_OIL",       "CBOT大豆油期货价格",         "L4", "AKShare接口待验证"),
            ("Y_COST_CNF",           "大豆进口成本CNF",            "L4", "付费订阅: 我的农产品网/Mysteel"),
            ("Y_STK_WARRANT",        "大商所豆油仓单",              "L4", "DCE接口待验证"),
            ("Y_POS_NET",            "大商所前20净持仓",            "L4", "DCE接口待验证"),
            ("Y_SPD_BASIS",          "豆油期现基差",                "L4", "豆油现货需AKShare验证"),
            ("Y_SPD_PALM_OIL",       "棕榈油-豆油价差(P-Y)",       "L4", "AKShare接口待验证"),
        ],
        "tier2": [
            ("Y_STK_COMMERCIAL",     "豆油商业库存",               "L4", "付费订阅: Mysteel/隆众"),
        ],
    },
    "PB": {
        "name": "沪铅",
        "exchange": "SHFE",
        "tier1": [
            ("PB_STK_BATTERY_RATE",  "铅酸蓄电池开工率",            "L4", "付费订阅: 隆众/卓创(必配)"),
            ("PB_STK_WARRANT",       "上期所沪铅仓单",             "L4", "SHFE接口待验证"),
            ("PB_SPD_BASIS",         "沪铅期现基差",               "L4", "SHFE/沪铅现货待验证"),
            ("PB_SPD_NEAR_FAR",      "沪铅近远月价差",             "L4", "SHFE接口待验证"),
            ("PB_FX_USDCNY",         "美元兑人民币汇率",           "L4", "L1已由其他品种采集"),
            ("PB_SPT_SMM",           "SMM铅现货报价",               "L4", "付费订阅: SMM"),
        ],
        "tier2": [
            ("PB_POS_NET",           "上期所前20净持仓",           "L4", "SHFE接口待验证"),
            ("PB_SPD_PRI_VIRGIN",   "原生/再生铅价差",             "L4", "付费订阅: SMM/隆众"),
            ("PB_MACRO_TC",          "铅矿加工费",                  "L4", "付费订阅: SMM"),
            ("PB_STK_SOCIAL",        "铅锭社会库存",                "L4", "付费订阅: SMM"),
        ],
    },
    "HC": {
        "name": "热轧卷板",
        "exchange": "DCE",
        "tier1": [
            ("HC_SPT_MYSTEEEL",     "Mysteel热轧卷板现货价格",    "L4", "Mysteel付费"),
            ("HC_STK_WARRANT",       "大商所热卷仓单",             "L4", "DCE接口待验证"),
            ("HC_POS_NET",           "大商所前20净持仓",            "L4", "DCE接口待验证"),
            ("HC_SPD_HC_RB",         "热轧-螺纹钢价差(HC-RB)",     "L4", "AKShare接口待验证"),
            ("HC_SPD_BASIS",         "热卷期现基差",               "L4", "Mysteel热卷现货需付费"),
            ("HC_SPD_NEAR_FAR",      "热卷近远月价差",             "L4", "AKShare接口待验证"),
        ],
        "tier2": [
            ("HC_STK_SOCIAL",        "热卷社会库存",               "L4", "Mysteel付费"),
            ("HC_SPD_HC_CC",         "热卷-冷轧价差",              "L4", "冷轧数据需Mysteel付费"),
            ("HC_MACRO_PMI_MFG",    "制造业PMI",                   "L4", "国家统计局月度"),
            ("HC_STK_OUTPUT_WEEKLY","热卷周度产量",                "L4", "付费订阅: Mysteel"),
            ("HC_MACRO_AUTO_OUTPUT","汽车产量同比",                 "L4", "中汽协/统计局"),
        ],
    },
}


def gen_runall(symbol: str, name: str, tier1: list, tier2: list) -> str:
    """生成 run_all.py"""
    all_scripts = []
    for code, _, layer, _ in tier1:
        script = symbol + "_" + code + ".py"
        all_scripts.append(script)

    scripts_list = ",\n    ".join('"' + s + '"' for s in all_scripts)

    # 直接在生成阶段用参数值替换
    _sym = symbol
    _name = name

    # 使用普通字符串拼接，避免 f-string 嵌套问题
    lines = [
        '#!/usr/bin/env python3',
        '# -*- coding: utf-8 -*-',
        f'"""',
        f'{symbol}（{name}）爬虫总控脚本',
        f'占位版本 - 待因子分析师推送付费数据源后开发',
        f'"""',
        'import os',
        'import sys',
        'import datetime',
        'import subprocess',
        'from pathlib import Path',
        '',
        'CURRENT_DIR = Path(__file__).parent',
        "LOG_DIR = CURRENT_DIR.parent / 'logs'",
        'LOG_DIR.mkdir(exist_ok=True)',
        '',
        'scripts = [',
        f'    {scripts_list}',
        ']',
        '',
        'def run_all():',
        '    _sym = "' + _sym + '"',
        '    _name = "' + _name + '"',
        '    now = datetime.datetime.now()',
        "    log_file = LOG_DIR / (now.strftime('%Y-%m-%d') + '_' + _sym + '.log')",
        '',
        '    print("=" * 50)',
        "    print('[STUB] " + _sym + " (" + _name + ") 占位版本')",
        '    print("待执行脚本数: " + str(len(scripts)))',
        '    print("=" * 50)',
        '',
        '    success_count = 0',
        '    failures = []',
        '',
        '    with open(log_file, "a", encoding="utf-8") as log:',
        "        sep50 = '=' * 50",
        "        log_write = sep50 + '\\n' + _sym + ' start @ ' + str(now) + '\\n' + sep50 + '\\n'",
        '        log.write(log_write)',
        '',
        '        for script in scripts:',
        '            script_path = CURRENT_DIR / script',
        "            if not script_path.exists():",
        "                msg = '[SKIP] 脚本不存在: ' + script",
        '                print("[WARN] " + msg)',
        "                log.write(msg + '\\n')",
        "                failures.append((script, '文件不存在'))",
        '                continue',
        '',
        '            print(">>> " + script + "...")',
        "            log.write('--- ' + script + ' @ ' + str(datetime.datetime.now()) + ' ---\\n')",
        '',
        '            cmd = [sys.executable, str(script_path), "--auto"]',
        '',
        '            try:',
        '                env = os.environ.copy()',
        '                env["PYTHONIOENCODING"] = "utf-8"',
        '                env["PYTHONUTF8"] = "1"',
        '',
        '                result = subprocess.run(',
        '                    cmd,',
        '                    stdout=subprocess.PIPE,',
        '                    stderr=subprocess.PIPE,',
        '                    encoding="utf-8",',
        '                    errors="replace",',
        '                    timeout=120,',
        '                    cwd=str(CURRENT_DIR),',
        '                    env=env,',
        '                )',
        '',
        '                log.write(result.stdout if result.stdout else "")',
        '                if result.stderr:',
        "                    log.write('[stderr] ' + result.stderr + '\\n')",
        '',
        '                if result.returncode == 0:',
        '                    success_count += 1',
        '                    print("[OK] " + script)',
        '                else:',
        '                    print("[WARN] " + script + " err=" + str(result.returncode))',
        "                    failures.append((script, 'err=' + str(result.returncode)))",
        '',
        '            except subprocess.TimeoutExpired:',
        "                msg = script + ' 超时'",
        '                print("[WARN] " + msg)',
        "                failures.append((script, '超时'))",
        '',
        '            except Exception as e:',
        "                msg = script + ' 异常: ' + str(e)",
        '                print("[WARN] " + msg)',
        "                failures.append((script, str(e)))",
        '',
        '        end_time = datetime.datetime.now()',
        '        duration = (end_time - now).total_seconds()',
        '',
        "        sep = '=' * 50",
        '        summary = "\\n" + sep + "\\n"',
        '        summary += _sym + " done @ " + str(end_time) + "\\n"',
        '        summary += "duration: " + str(round(duration, 1)) + "s\\n"',
        '        summary += "success: " + str(success_count) + "/" + str(len(scripts)) + "\\n"',
        '        if failures:',
        '            summary += "failed " + str(len(failures)) + "\\n"',
        '            for n, r in failures:',
        '                summary += "  - " + n + ": " + r + "\\n"',
        '        else:',
        "            summary += 'all ok\\n'",
        '        summary += sep + "\\n"',
        '',
        '        log.write(summary)',
        '        print(summary)',
        '',
        '',
        'if __name__ == "__main__":',
        '    run_all()',
        '',
    ]
    return '\n'.join(lines)


def gen_stub_script(symbol: str, code: str, name: str, layer: str, reason: str) -> str:
    """生成单个因子的 stub 爬虫脚本"""
    fc = symbol + '_' + code
    lines = [
        '#!/usr/bin/env python3',
        '# -*- coding: utf-8 -*-',
        '"""',
        symbol + ' ' + name,
        fc,
        '',
        '[跳过] 待开发',
        '原因: ' + reason,
        '数据层: ' + layer,
        '',
        '付费订阅: 如需激活此因子，请联系因子分析师配置付费数据源',
        '"""',
        'import sys',
        'import datetime',
        'from pathlib import Path',
        '',
        '# 尝试导入通用模块',
        'try:',
        "    sys.path.insert(0, str(Path(__file__).parent.parent / 'common'))",
        '    from io_win import fix_encoding',
        '    fix_encoding()',
        'except ImportError:',
        '    pass',
        '',
        'try:',
        '    from common.db_utils import save_to_db, get_pit_dates',
        'except ImportError:',
        '    def save_to_db(*a, **kw): pass',
        '    def get_pit_dates():',
        '        today = datetime.date.today()',
        '        dow = today.weekday()',
        '        if dow == 0:',
        '            obs = today - datetime.timedelta(days=3)',
        '        elif dow >= 5:',
        '            obs = today - datetime.timedelta(days=dow - 4)',
        '        else:',
        '            obs = today',
        '        return obs, today',
        '',
        '# 因子参数（在函数外捕获值）',
        '_FACTOR_SYMBOL = "' + symbol + '"',
        '_FACTOR_CODE = "' + code + '"',
        '_FACTOR_NAME = "' + name + '"',
        '_FACTOR_FC = "' + fc + '"',
        '_FACTOR_REASON = "' + reason + '"',
        '',
        '',
        'def run(auto=False):',
        '    obs_date, pub_date = get_pit_dates()',
        '    print("[跳过] " + _FACTOR_FC + " = None (obs=" + str(obs_date) + ")")',
        '    print("      原因: " + _FACTOR_REASON)',
        '',
        '    if not auto:',
        "        print('\\n提示: 使用 --auto 参数可跳过此确认')",
        '',
        '    # 写入 L4 stub 记录，value = None',
        '    try:',
        '        save_to_db(',
        '            symbol=_FACTOR_SYMBOL,',
        '            factor_code=_FACTOR_FC,',
        '            obs_date=obs_date,',
        '            pub_date=pub_date,',
        '            raw_value=None,',
        '            source="占位(付费订阅待配)",',
        '            source_confidence=0.5,',
        '            notes="[STUB] " + _FACTOR_REASON,',
        '        )',
        '        print("[OK] 已写入 stub 记录 (source_confidence=0.5)")',
        '    except Exception as e:',
        '        print("[WARN] DB写入失败: " + str(e))',
        '',
        '    return 0',
        '',
        '',
        'if __name__ == "__main__":',
        '    auto = "--auto" in sys.argv',
        '    sys.exit(run(auto=auto))',
        '',
    ]
    return '\n'.join(lines)


def main():
    for symbol, info in SPECIES.items():
        name = info["name"]
        tier1 = info["tier1"]
        tier2 = info["tier2"]

        dir_path = ROOT / symbol
        dir_path.mkdir(exist_ok=True)

        # 写 run_all.py
        runall_content = gen_runall(symbol, name, tier1, tier2)
        runall_path = dir_path / f"{symbol}_run_all.py"
        with open(runall_path, "w", encoding="utf-8") as f:
            f.write(runall_content)
        print(f"  [OK] {runall_path}")

        # 写每个因子的 stub 脚本
        for code, fname, layer, reason in tier1 + tier2:
            script_name = f"{symbol}_{code}.py"
            content = gen_stub_script(symbol, code, fname, layer, reason)
            with open(dir_path / script_name, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"    [OK] {script_name}")

    print(f"\\n共创建 {len(SPECIES)} 个品种目录和 stub 脚本")
    print("待因子分析师推送付费数据源后，可逐个替换 stub 为正式爬虫")


if __name__ == "__main__":
    main()
