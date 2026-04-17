"""
generate_games_cache.py
───────────────────────
Generates games-cache.json for Tabletop Power Rankings.

Uses the BGG /thing API to fetch name, year and thumbnail
for a curated list of top ~1000 BGG game IDs.

Usage:
  BGG_TOKEN="your-token" python generate_games_cache.py
  BGG_TOKEN="your-token" python generate_games_cache.py --out ~/bg-power-ranking/
  BGG_TOKEN="your-token" python generate_games_cache.py --users myname --month 2026-03
"""

import json, os, sys, time, xml.etree.ElementTree as ET, argparse, calendar
from pathlib import Path
from datetime import datetime
import requests

# ── Top ~1000 BGG game IDs by rank (early 2026) ───────────────────────────────
TOP_IDS = [
    174430,233078,291457,224517,167791,316554,169786,266192,162886,342942,
    237182,220308,182028,193738,312484,115746,187645,128621,255984,246784,
    161936,276025,295947,173346,233867,251247,284083,264220,285967,312169,
    291572,198928,269385,246900,303672,215312,236457,261393,150376,172818,
    12333,31260,124361,126163,224421,170042,281549,324856,164153,175640,
    40692,72125,230802,287954,220877,262543,311736,201808,266524,163412,
    228341,178900,255092,250458,205059,155426,284378,2651,68448,9209,
    14996,30549,63268,43111,110308,25613,84876,148228,39856,104162,
    175914,180263,121408,324706,35677,13,37111,216132,244522,65244,
    145017,184001,153408,159675,209685,356546,318977,283864,320184,354986,
    354582,344672,343376,359441,324696,334986,328479,349067,271025,306028,
    334947,359970,374545,338627,336986,344905,332289,383171,382518,380152,
    366161,356435,371942,374173,359572,352515,383117,351538,330592,357563,
    366013,379078,297550,269994,282524,300531,253284,332772,171623,243454,
    278306,193037,181304,188834,213038,147020,161533,213953,2655,300905,
    311022,317985,306068,278416,339906,275637,320900,363369,385761,311031,
    289169,254640,295654,316153,316180,350044,235457,222975,238917,193949,
    238690,247030,192091,218219,200818,215671,234609,258779,259490,270844,
    10547,230181,303940,132531,229853,251658,288939,293836,128882,172081,
    255584,199042,217861,146021,168435,188819,206718,218603,229818,241266,
    258489,193838,281624,309360,199792,185343,205637,184267,163166,191189,
    209778,276931,256960,107529,55690,70323,182134,191570,98778,39684,
    118,188,171,687,40,372,3532,1406,181,2407,5048,2921,
    358616,303954,301767,295137,283862,383052,351570,339789,316779,253807,
    166669,120677,250727,308025,287482,186994,254071,308765,346406,
    209685,222975,238917,295054,297030,281624,309360,
    385761,381121,312853,187191,227789,300531,317985,282524,311022,
    332772,243454,278306,193037,181304,147020,161533,
    244522,2651,9209,14996,43111,63268,201808,266524,275637,320900,
    30549,161936,246784,320184,162886,278416,306068,339906,187645,
    178900,188834,213038,228341,255092,181304,161533,39856,148228,
    2655,213953,171,188,687,12333,115746,37111,
    324706,256960,166669,120677,96848,280132,314088,261541,
]

def get_session(token):
    s = requests.Session()
    s.headers.update({
        "User-Agent": "tabletop-power-rankings/1.0",
        "Authorization": f"Bearer {token}",
    })
    return s

def fetch_details(ids, session, batch_size=20):
    result = {}
    total  = len(ids)
    for i in range(0, total, batch_size):
        batch  = ids[i:i+batch_size]
        id_str = ",".join(str(x) for x in batch)
        url    = f"https://boardgamegeek.com/xmlapi2/thing?id={id_str}&type=boardgame"
        for attempt in range(4):
            try:
                r = session.get(url, timeout=30)
                if r.status_code == 202:
                    time.sleep(4); continue
                if r.status_code != 200:
                    print(f"  HTTP {r.status_code} batch {i//batch_size+1}")
                    break
                root = ET.fromstring(r.content)
                for item in root.findall("item"):
                    gid     = item.get("id","")
                    name_el = item.find("name[@type='primary']")
                    name    = name_el.get("value","") if name_el is not None else ""
                    year_el = item.find("yearpublished")
                    year    = year_el.get("value","") if year_el is not None else ""
                    th_el   = item.find("thumbnail")
                    thumb   = (th_el.text or "").strip() if th_el is not None else ""
                    if gid and name:
                        result[int(gid)] = {"name":name,"year":year,"thumb":thumb}
                break
            except Exception as e:
                print(f"  Error: {e}"); time.sleep(3)
        done = min(i+batch_size, total)
        print(f"  {done}/{total} games fetched...", end="\r")
        time.sleep(1.1)
    print()
    return result

def fetch_plays(username, month, session):
    year, mon = month.split("-")
    last_day  = calendar.monthrange(int(year), int(mon))[1]
    min_date  = f"{year}-{mon}-01"
    max_date  = f"{year}-{mon}-{last_day:02d}"
    plays, page = {}, 1
    while True:
        url = (f"https://boardgamegeek.com/xmlapi2/plays"
               f"?username={username}&mindate={min_date}&maxdate={max_date}"
               f"&type=thing&subtype=boardgame&page={page}")
        r = session.get(url, timeout=30)
        if r.status_code != 200: break
        root = ET.fromstring(r.content)
        page_plays = root.findall("play")
        if not page_plays: break
        for play in page_plays:
            qty = int(play.get("quantity",1))
            for item in play.findall("item"):
                oid  = item.get("objectid","")
                name = item.get("name","")
                if oid:
                    if oid not in plays:
                        plays[oid] = {"id":oid,"name":name,"plays":0}
                    plays[oid]["plays"] += qty
        total   = int(root.get("total",0))
        if page*100 >= total or len(page_plays) < 100: break
        page += 1
        time.sleep(1.1)
    return sorted(plays.values(), key=lambda x: -x["plays"])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=".", help="Output directory")
    parser.add_argument("--users", nargs="+", default=[])
    parser.add_argument("--month", default=datetime.today().strftime("%Y-%m"))
    parser.add_argument("--skip-games", action="store_true")
    args = parser.parse_args()

    token = os.environ.get("BGG_TOKEN","")
    if not token:
        print("Error: BGG_TOKEN not set")
        print("Usage: BGG_TOKEN='your-token' python generate_games_cache.py")
        sys.exit(1)

    session = get_session(token)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not args.skip_games:
        unique_ids = list(dict.fromkeys(TOP_IDS))
        print(f"\n── Fetching {len(unique_ids)} games from BGG ──")
        details = fetch_details(unique_ids, session)
        print(f"  Got data for {len(details)} games")

        cache = []
        for gid in unique_ids:
            if gid in details:
                d = details[gid]
                cache.append({"id":str(gid),"name":d["name"],"year":d["year"],"thumb":d["thumb"]})

        out_path = out_dir / "games-cache.json"
        with open(out_path,"w",encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        print(f"\n✅ games-cache.json → {out_path} ({len(cache)} games)")

    if args.users:
        print(f"\n── Fetching plays for {args.users} in {args.month} ──")
        all_plays = {}
        for username in args.users:
            plays = fetch_plays(username, args.month, session)
            all_plays[username] = plays
            print(f"  {username}: {len(plays)} games")
            for p in plays[:5]:
                print(f"    {p['plays']}x {p['name']}")

        plays_path = out_dir / "plays-export.json"
        with open(plays_path,"w",encoding="utf-8") as f:
            json.dump({"month":args.month,"users":all_plays}, f, ensure_ascii=False, indent=2)
        print(f"\n✅ plays-export.json → {plays_path}")

    print("\nDone.")

if __name__ == "__main__":
    main()
