#!/usr/bin/env python3
"""
拆分合并的词根/词缀条目，重新斟酌释义，搜索真实关联单词。
用法: python3 rebuild_roots_affixes.py --host localhost --user root --password '...' --database english_new [--dry-run] [--apply]
--dry-run（默认）：只打印计划，不改数据库
--apply：真正执行（TRUNCATE + 重建 roots/affixes + 关联 root_words/affix_words）
"""
import argparse
import pymysql

ROOTS = [
    [("un-", "不……的（否定前缀）", ["unhappy", "unable", "unknown", "undo", "unfair"])],
    [
        ("a-", "不，无（否定前缀，用于辅音前）", ["atypical", "amoral", "asymmetric", "apolitical"]),
        ("ab-", "离开，相反", ["abnormal", "abduct", "abuse", "abolish"]),
        ("abs-", "离开，相反", ["abstract", "abstain", "absorb", "absent"]),
    ],
    [
        ("acc-", "向，朝；加强语气（ad- 在 c 前的同化形式）", ["accept", "accord", "accuse", "accompany"]),
        ("acq-", "向，朝；加强语气（ad- 在 qu 前的同化形式）", ["acquire", "acquaint"]),
        ("add-", "向，朝；加强语气（ad- 在 d 前的同化形式）", ["add", "addict"]),
        ("aff-", "向，朝；加强语气（ad- 在 f 前的同化形式）", ["affair", "affect", "afford"]),
        ("agg-", "向，朝；加强语气（ad- 在 g 前的同化形式）", ["aggression", "aggressive"]),
        ("app-", "向，朝；加强语气（ad- 在 p 前的同化形式）", ["approach", "applaud", "apply", "appear"]),
        ("arr-", "向，朝；加强语气（ad- 在 r 前的同化形式）", ["arrive", "arrange", "arrest"]),
        ("att-", "向，朝；加强语气（ad- 在 t 前的同化形式）", ["attract", "attend", "attach", "attempt"]),
    ],
    [
        ("ante-", "……之前，在前（拉丁语源）", ["anticipate", "antique", "antenatal", "anteroom"]),
        ("anti-", "反对，抵抗（希腊语源）", ["antibiotic", "antisocial", "antivirus", "antibody"]),
        ("ant-", "反对，抵抗（anti- 在元音前的省音形式）", ["antacid"]),
    ],
    [("beni-", "好，善", ["benefit", "beneficial"])],
    [
        ("bi-", "二，双", ["bicycle", "bilingual", "bipolar"]),
        ("bin-", "二，双", ["binary"]),
        ("di-", "二，双（希腊语源）", ["dioxide", "dilemma", "diploma"]),
        ("dia-", "穿过，横过（注意与“二”无关，希腊语源）", ["diagram", "dialogue", "diagonal", "diameter"]),
    ],
    [("by-", "旁边，副的", ["bypass", "byproduct", "bystander"])],
    [
        ("co-", "共同，一起", ["cooperate", "coexist", "coauthor"]),
        ("col-", "共同，一起（com- 在 l 前的同化形式）", ["collect", "collaborate", "collide"]),
        ("cor-", "共同，一起（com- 在 r 前的同化形式）", ["correspond", "corrupt"]),
        ("com-", "共同，一起", ["combine", "compare", "compose"]),
        ("con-", "共同，一起", ["connect", "contact", "construct"]),
    ],
    [
        ("contra-", "相反，反对", ["contradict", "contrast", "contrary"]),
        ("counter-", "相反，反对", ["counterattack", "counterpart", "counterclockwise"]),
    ],
    [("de-", "1.向下 2.去除，相反 3.加强语气", ["descend", "destroy", "decrease", "depart"])],
    [
        ("demi-", "半", []),
        ("hemi-", "半", ["hemisphere"]),
        ("semi-", "半", ["semicircle", "semifinal", "semiconductor"]),
    ],
    [
        ("dis-", "1.相反，不 2.分开", ["disagree", "disappear", "distrust", "disconnect"]),
        ("dif-", "分开，相反（dis- 在 f 前的同化形式）", ["differ", "difficult", "diffuse"]),
    ],
    [
        ("e-", "出，向外", ["emerge", "evade", "erupt"]),
        ("ex-", "出，向外；曾经的……", ["exit", "expand", "exclude"]),
        ("es-", "出，向外（ex- 的古法语变体）", ["escape"]),
        ("ec-", "出，向外（希腊语中 ex- 的变体）", ["eccentric", "ecstasy"]),
    ],
    [
        ("em-", "使……；进入（en- 在 b/p 前的同化形式）", ["embrace", "empower", "embed"]),
        ("en-", "使……；进入", ["enable", "encourage", "enjoy", "enlarge"]),
    ],
    [
        ("extra-", "超过，……以外，额外", ["extraordinary", "extracurricular"]),
        ("extro-", "向外", ["extroverted"]),
    ],
    [
        ("fore-", "前面，预先", ["forecast", "foresee", "forehead"]),
        ("for-", "禁止，除去（与 fore- 意义不同，勿混淆）", ["forbid", "forget", "forgive"]),
    ],
    [
        ("in-", "1.不，非 2.向内", ["incorrect", "inactive", "insert", "include"]),
        ("im-", "1.不，非 2.向内（in- 在 b/m/p 前的同化形式）", ["impossible", "immortal", "import"]),
        ("il-", "不，非（in- 在 l 前的同化形式）", ["illegal", "illogical"]),
        ("ir-", "不，非（in- 在 r 前的同化形式）", ["irregular", "irrelevant"]),
    ],
    [("inter-", "在……之间，相互", ["international", "internet", "interact"])],
    [
        ("ob-", "反对，朝向；加强语气", ["object", "obstacle", "observe"]),
        ("op-", "反对（ob- 在 p 前的同化形式）", ["oppose", "opponent", "opportunity"]),
    ],
    [("para-", "1.在旁边 2.类似，辅助", ["parallel", "paradox", "paramedic"])],
    [("per-", "彻底，贯穿", ["perform", "permit", "persist", "perfect"])],
    [("pre-", "提前，预先", ["prepare", "predict", "preview", "prevent"])],
    [("pro-", "1.向前 2.支持，代替", ["progress", "promote", "produce", "proceed"])],
    [("re-", "1.反复，又，再 2.相反 3.返回，回来", ["return", "repeat", "review", "recall"])],
    [
        ("sub-", "1.在下面 2.次级，亚", ["submarine", "subway", "subtitle"]),
        ("sup-", "在下面（sub- 在 p 前的同化形式）", ["support", "suppress", "suppose"]),
        ("suc-", "在下面（sub- 在 c 前的同化形式）", ["succeed", "succumb"]),
        ("suf-", "在下面（sub- 在 f 前的同化形式）", ["suffer", "sufficient", "suffix"]),
    ],
    [
        ("sim-", "相似，相同", ["similar", "simultaneous"]),
        ("sym-", "共同，相同（syn- 在 b/p/m 前的同化形式）", ["symbol", "sympathy", "symphony"]),
        ("syn-", "共同，相同", ["synonym", "synthesis", "syndrome"]),
        ("syl-", "共同（syn- 在 l 前的同化形式）", ["syllable"]),
    ],
    [("trans-", "穿，传，转", ["transport", "translate", "transform"])],
    [
        ("twi-", "二，两个", ["twin", "twilight"]),
        ("tri-", "三", ["triangle", "tricycle", "triple"]),
    ],
    [("an-", "不，无（否定前缀，用于元音前）", ["anonymous", "anarchy", "anemia"])],
    [("with-", "相反，对抗；共同", ["withdraw", "withstand"])],
]

AFFIXES = [
    [("-or", "……的人", ["doctor", "actor", "mentor", "professor", "inspector", "director", "editor", "visitor", "sailor", "sponsor"])],
    [("-er", "……的人", ["teacher", "writer", "farmer", "worker", "leader", "banker", "singer", "driver", "painter", "reporter"])],
    [("-eer", "……的人", ["engineer", "volunteer", "pioneer", "mountaineer"])],
    [("-ee", "被……的人（名词后缀）", ["employee", "trainee", "refugee", "interviewee", "nominee"])],
    [
        ("-able", "可……的，能……的", ["comfortable", "reasonable", "acceptable", "available"]),
        ("-ible", "可……的，能……的", ["possible", "visible", "flexible", "responsible"]),
    ],
    [("-acy", "名词后缀，表示性质、状态", ["accuracy", "privacy", "diplomacy"])],
    [("-age", "名词后缀，表示集合、状态、行为", ["marriage", "package", "courage", "village"])],
    [
        ("-al", "形容词后缀，表示……的", ["national", "natural", "personal", "cultural"]),
        ("-ar", "形容词后缀，表示……的", ["popular", "familiar", "regular"]),
        ("-an", "形容词/名词后缀，表示……的，属于……的人", ["American", "human", "urban"]),
    ],
    [
        ("-ancy", "名词后缀，表示状态、性质", ["vacancy", "pregnancy"]),
        ("-ance", "名词后缀，表示状态、行为", ["distance", "importance", "performance"]),
        ("-ency", "名词后缀，表示状态、性质", ["efficiency", "emergency", "frequency"]),
        ("-ence", "名词后缀，表示状态、行为", ["difference", "confidence", "evidence"]),
    ],
    [
        ("-ant", "……的（形容词）或……的人/物（名词）", ["important", "pleasant", "assistant"]),
        ("-ent", "……的（形容词）或……的人/物（名词）", ["different", "student", "president"]),
    ],
    [
        ("-ary", "名词/形容词后缀，与……有关的（地方，物）", ["dictionary", "library", "secretary"]),
        ("-ery", "名词后缀，表示场所、行为、性质", ["bakery", "robbery", "delivery"]),
        ("-ory", "名词/形容词后缀，表示场所、性质", ["factory", "memory", "laboratory"]),
    ],
    [
        ("-ate", "动词/形容词/名词后缀，使……，具有……性质的", ["create", "celebrate", "graduate"]),
        ("-ite", "名词/形容词后缀", ["favorite", "definite", "opposite"]),
        ("-ute", "动词后缀", ["contribute", "distribute", "execute"]),
    ],
    [
        ("-icle", "名词后缀，表示小的东西", ["article", "particle", "vehicle"]),
        ("-cule", "名词后缀，表示微小的东西", ["molecule"]),
    ],
    [("-dom", "名词后缀，表示领域、状态、性质", ["freedom", "kingdom", "wisdom", "boredom"])],
    [("-ed", "形容词/动词后缀，表示过去式，具有……特征的", ["excited", "tired", "interested"])],
    [("-en", "动词后缀，使……", ["widen", "strengthen", "weaken", "shorten"])],
    [("-ur", "名词后缀，表示人、物（较少见）", ["amateur"])],
    [("-et", "名词后缀，常表示小的东西", ["booklet", "bracelet", "tablet"])],
    [
        ("-fy", "动词后缀，表示使……", ["satisfy"]),
        ("-ify", "动词后缀，表示使……", ["identify", "classify", "simplify", "clarify"]),
    ],
    [("-ful", "形容词后缀，表示充满的，具有……特点的", ["beautiful", "helpful", "careful", "powerful"])],
    [("-hood", "名词后缀，表示状态或性质", ["childhood", "neighborhood", "brotherhood"])],
    [("-ic", "形容词后缀，表示……的", ["basic", "historic", "magic", "classic"])],
    [("-ics", "名词后缀，常表示……学，……学问", ["physics", "mathematics", "economics", "politics"])],
    [("-id", "形容词/名词后缀", ["solid", "rapid", "acid"])],
]


def find_word_ids(cur, candidates, limit=10):
    ids = []
    for w in candidates:
        if len(ids) >= limit:
            break
        cur.execute("SELECT id FROM words WHERE word = %s AND deleted_at IS NULL LIMIT 1", (w,))
        row = cur.fetchone()
        if row:
            ids.append((w, row["id"]))
    return ids


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--user", default="root")
    parser.add_argument("--password", required=True)
    parser.add_argument("--database", default="english_new")
    parser.add_argument("--apply", action="store_true", help="真正执行写入，不加则只是 dry-run")
    args = parser.parse_args()

    conn = pymysql.connect(
        host=args.host, user=args.user, password=args.password, database=args.database,
        charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
    )
    cur = conn.cursor()

    total_roots = sum(len(group) for group in ROOTS)
    total_affixes = sum(len(group) for group in AFFIXES)
    print(f"计划：roots {len(ROOTS)} 行 -> {total_roots} 行；affixes {len(AFFIXES)} 行 -> {total_affixes} 行")

    no_example_roots = []
    no_example_affixes = []

    if not args.apply:
        print("\n=== DRY RUN，只做单词匹配检查，不改数据库 ===\n")
        for group in ROOTS:
            for name, meaning, candidates in group:
                found = find_word_ids(cur, candidates)
                if not found:
                    no_example_roots.append(name)
                print(f"[root] {name:12s} {meaning:40s} 例词({len(found)}): {[w for w,_ in found]}")
        for group in AFFIXES:
            for name, meaning, candidates in group:
                found = find_word_ids(cur, candidates)
                if not found:
                    no_example_affixes.append(name)
                print(f"[affix] {name:8s} {meaning:40s} 例词({len(found)}): {[w for w,_ in found]}")
        print(f"\n没搜到任何例词的词根: {no_example_roots}")
        print(f"没搜到任何例词的词缀: {no_example_affixes}")
        conn.close()
        return

    # --apply: 真正执行
    print("\n=== 执行：重建 roots / affixes / root_words / affix_words ===")
    cur.execute("DELETE FROM root_words")
    cur.execute("DELETE FROM affix_words")
    cur.execute("DELETE FROM roots")
    cur.execute("DELETE FROM affixes")
    conn.commit()

    root_word_rows = []
    for group in ROOTS:
        for name, meaning, candidates in group:
            cur.execute(
                "INSERT INTO roots (name, meaning) VALUES (%s, %s)", (name, meaning)
            )
            root_id = cur.lastrowid
            found = find_word_ids(cur, candidates)
            if not found:
                no_example_roots.append(name)
            for _, word_id in found:
                root_word_rows.append((root_id, word_id))
    conn.commit()

    affix_word_rows = []
    for group in AFFIXES:
        for name, meaning, candidates in group:
            cur.execute(
                "INSERT INTO affixes (name, meaning) VALUES (%s, %s)", (name, meaning)
            )
            affix_id = cur.lastrowid
            found = find_word_ids(cur, candidates)
            if not found:
                no_example_affixes.append(name)
            for _, word_id in found:
                affix_word_rows.append((affix_id, word_id))
    conn.commit()

    if root_word_rows:
        cur.executemany(
            "INSERT INTO root_words (root_id, word_id) VALUES (%s, %s)", root_word_rows
        )
    if affix_word_rows:
        cur.executemany(
            "INSERT INTO affix_words (affix_id, word_id) VALUES (%s, %s)", affix_word_rows
        )
    conn.commit()

    cur.execute("SELECT COUNT(*) c FROM roots")
    print("roots 行数:", cur.fetchone()["c"])
    cur.execute("SELECT COUNT(*) c FROM affixes")
    print("affixes 行数:", cur.fetchone()["c"])
    cur.execute("SELECT COUNT(*) c FROM root_words")
    print("root_words 关联数:", cur.fetchone()["c"])
    cur.execute("SELECT COUNT(*) c FROM affix_words")
    print("affix_words 关联数:", cur.fetchone()["c"])
    print("没搜到例词的词根:", no_example_roots)
    print("没搜到例词的词缀:", no_example_affixes)

    conn.close()


if __name__ == "__main__":
    main()
