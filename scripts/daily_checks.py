#!/usr/bin/env python3
"""Independent artifact checks for daily-task fixtures; no model judge.

Exit 0: pass; 1: unmet task requirements; 2: checker/input configuration error.
Only data is read from agent files. Agent output is never imported or executed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys


def expand(value, base_url):
    if isinstance(value, str):
        return value.replace("{{WEB}}", base_url)
    if isinstance(value, list):
        return [expand(x, base_url) for x in value]
    if isinstance(value, dict):
        return {k: expand(v, base_url) for k, v in value.items()}
    return value


def safe_file(root, name):
    relative = Path(name)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise ValueError(f"Unsafe relative path: {name!r}")
    candidate = root / relative
    for parent in [candidate, *candidate.parents]:
        if parent == root:
            break
        if parent.is_symlink():
            raise ValueError(f"Symlinks are not accepted: {name}")
    if not candidate.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Path escapes workspace: {name}")
    return candidate


def read_text(root, name):
    path = safe_file(root, name)
    if not path.is_file():
        raise ValueError(f"Missing artifact: {name}")
    if path.stat().st_size > 2_000_000:
        raise ValueError(f"Artifact exceeds 2 MB: {name}")
    return path.read_text(encoding="utf-8")


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"Duplicate JSON key: {key}")
        value[key] = item
    return value


def read_json(root, name):
    return json.loads(read_text(root, name), object_pairs_hook=unique_object,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(f"Non-finite JSON number: {x}")))


def canonical(value):
    """Ignore record order, accept equivalent aware instants, retain data types."""
    if isinstance(value, dict):
        return ("object", tuple(sorted((k, canonical(v)) for k, v in value.items())))
    if isinstance(value, list):
        return ("array", tuple(sorted((canonical(x) for x in value), key=repr)))
    if isinstance(value, bool) or value is None:
        return ("bool" if isinstance(value, bool) else "null", value)
    if isinstance(value, (int, float)):
        return ("number", value)
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})", value):
        try:
            return ("instant", datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat())
        except ValueError:
            pass
    return ("string", value)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def integer(value, name, minimum=0):
    require(type(value) is int and value >= minimum, f"{name} must be an integer >= {minimum}")
    return value


def keyed(items, key):
    require(isinstance(items, list) and all(isinstance(x, dict) for x in items), "Expected a list of objects")
    require(all(isinstance(x.get(key), str) for x in items), f"Each record needs string {key}")
    result = {x[key]: x for x in items}
    require(len(result) == len(items), f"Duplicate {key} records")
    return result


def check_meals(output, rules):
    require(isinstance(output, dict), "Meal result must be an object")
    require(set(output) == {"dinners", "leftover_lunches", "shopping", "cost_cents"}, "Unexpected meal result fields")
    days = {x["date"]: x for x in rules["days"]}
    dinners = keyed(output["dinners"], "date")
    lunches = keyed(output["leftover_lunches"], "date")
    recipes = {x["id"]: x for x in rules["recipes"]}
    require(set(dinners) == set(days), "Dinner dates do not match all requested days")
    require(set(lunches) == set(rules["leftover_lunch_dates"]), "Leftover lunch dates do not match the request")
    reserved = {date: 0 for date in days}
    for date, lunch in lunches.items():
        require(set(lunch) == {"date", "from_dinner_date", "servings"}, "Unexpected lunch fields")
        previous = lunch["from_dinner_date"]
        require(previous in dinners and previous < date, "Leftovers must come from an earlier dinner")
        require(integer(lunch["servings"], "Lunch servings", 1) == 1, "Each requested lunch is for one person")
        reserved[previous] += lunch["servings"]
    used_recipes = set()
    quantities = {item: 0 for item in rules["unit_prices_cents"]}
    for date, dinner in dinners.items():
        require(set(dinner) == {"date", "recipe_id", "servings"}, "Unexpected dinner fields")
        recipe = recipes.get(dinner["recipe_id"])
        require(recipe is not None, "Unknown recipe")
        require(recipe["minutes"] <= days[date]["max_minutes"], f"Cooking limit exceeded on {date}")
        servings = integer(dinner["servings"], "Dinner servings", 1)
        require(servings == days[date]["servings"] + reserved[date], f"Portions do not reconcile on {date}")
        used_recipes.add(recipe["id"])
        for item, qty in recipe["ingredients_per_serving"].items():
            quantities[item] += qty * servings
    require(len(used_recipes) >= rules["minimum_distinct_recipes"], "Insufficient recipe variety")
    shopping = {item: max(0, qty - rules["pantry"].get(item, 0)) for item, qty in quantities.items()}
    require(isinstance(output["shopping"], dict), "Shopping must be an object")
    for item, qty in output["shopping"].items():
        integer(qty, f"Shopping quantity {item}")
    require(output["shopping"] == shopping, "Shopping quantities do not reconcile with portions and pantry")
    cost = sum(qty * rules["unit_prices_cents"][item] for item, qty in shopping.items())
    require(integer(output["cost_cents"], "Cost") == cost, "Shopping cost is incorrect")
    require(cost <= rules["budget_cents"], "Shopping exceeds budget")


def minutes(value):
    require(isinstance(value, str) and re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value), "Use valid HH:MM times")
    h, m = map(int, value.split(":"))
    return h * 60 + m


def check_itinerary(output, rules):
    require(isinstance(output, dict) and set(output) == {"date", "stops", "hotel_return"}, "Unexpected itinerary fields")
    require(output["date"] == rules["date"], "Wrong trip date")
    stops = keyed(output["stops"], "id")
    require(set(stops) == set(rules["required_ids"]), "Visit exactly the required attractions")
    require(not (set(stops) & set(rules["unavailable_ids"])), "An unavailable stop remains in the itinerary")
    attractions = {x["id"]: x for x in rules["attractions"]}
    previous, end, driving = "hotel", minutes(rules["departure"]), 0
    for stop in output["stops"]:
        require(set(stop) == {"id", "arrival", "departure"}, "Unexpected stop fields")
        attraction = attractions[stop["id"]]
        leg = rules["travel_minutes"][previous][stop["id"]]
        arrival, departure = minutes(stop["arrival"]), minutes(stop["departure"])
        require(arrival >= end + leg, "Travel time or chronological order is infeasible")
        require(arrival >= minutes(attraction["open"]) and departure <= minutes(attraction["close"]), "Visit lies outside opening hours")
        require(departure - arrival >= attraction["minutes"], "Insufficient visit duration")
        if stop["id"] == rules["fixed_reservation"]["id"]:
            require(arrival == minutes(rules["fixed_reservation"]["arrival"]), "Fixed reservation was moved")
        previous, end, driving = stop["id"], departure, driving + leg
    leg = rules["travel_minutes"][previous]["hotel"]
    driving += leg
    returned = minutes(output["hotel_return"])
    require(returned >= end + leg and returned <= minutes(rules["hotel_return_by"]), "Hotel return time is infeasible")
    require(driving <= rules["max_drive_minutes"], "Daily driving limit exceeded")


def check_organize(output, rules, root):
    require(isinstance(output, dict) and set(output) == {"moves"}, "Unexpected move manifest fields")
    moves = keyed(output["moves"], "from")
    require(set(moves) == set(rules["original_sha256"]), "Manifest must account for every original file exactly once")
    destinations = set()
    for original, move in moves.items():
        require(set(move) == {"from", "to"}, "Unexpected move fields")
        destination = move["to"]
        require(isinstance(destination, str), "Destination must be a path")
        path = safe_file(root, destination)
        prefix = "organized/" + rules["categories"][original] + "/"
        require(destination.startswith(prefix), f"Wrong category folder for {original}")
        require(destination not in destinations, "Colliding destinations")
        destinations.add(destination)
        require(path.is_file(), f"Missing destination {destination}")
        require(hashlib.sha256(path.read_bytes()).hexdigest() == rules["original_sha256"][original], f"File content changed: {original}")
        require(not safe_file(root, original).exists(), f"Original file was copied instead of moved: {original}")
    actual = {p.relative_to(root).as_posix() for p in (root / "organized").rglob("*") if p.is_file() or p.is_symlink()}
    require(actual == destinations, "Organized tree contains untracked extra files")
    require(not any(p.is_file() or p.is_symlink() for p in (root / "inbox").rglob("*")), "Inbox contains unaccounted files")


def check_case(case, variant, workspace, base_url="http://fixture.invalid", *, snapshots=None, requests=()):
    data = expand(case["variants"][variant], base_url)
    workspace = Path(workspace).resolve()
    checks = []
    removed = {name for phase in data["phases"] for name in phase.get("remove_before", [])}
    mutable = set(data["mutable_inputs"])
    for name, original in data["files"].items():
        if name in removed or name in mutable:
            continue
        try:
            require(read_text(workspace, name) == original, f"Read-only input was changed: {name}")
            checks.append({"check": "input:" + name, "passed": True})
        except (OSError, ValueError, UnicodeError) as exc:
            checks.append({"check": "input:" + name, "passed": False, "error": str(exc)})
    for spec in data["checks"]:
        label = spec["kind"] + ":" + spec["path"]
        try:
            check_root = Path(snapshots) / f"phase-{spec['phase']:02d}" if spec.get("phase") and snapshots else workspace
            if spec.get("phase"):
                require(snapshots is not None, "Phase snapshot is required to grade this artifact")
            if spec["kind"] == "retrieval":
                for path, status in spec["required"].items():
                    require(any(r.get("path") == path and r.get("status") == status for r in requests), f"No recorded HTTP retrieval: {path} ({status})")
            elif spec["kind"] == "text":
                text = read_text(check_root, spec["path"])
                require(len(text.strip()) >= spec["min_chars"], "Artifact is too short")
                for phrase in spec.get("contains", []):
                    require(phrase.casefold() in text.casefold(), f"Missing required text: {phrase}")
                for phrase in spec.get("absent", []):
                    require(phrase.casefold() not in text.casefold(), f"Forbidden text remains: {phrase}")
            else:
                output = read_json(check_root, spec["path"])
                if spec["kind"] == "json":
                    require(canonical(output) == canonical(spec["expected"]), "Structured facts differ from expected facts (see reviewer check specification)")
                elif spec["kind"] == "meals":
                    check_meals(output, spec["rules"])
                elif spec["kind"] == "organize":
                    check_organize(output, spec["rules"], workspace)
                elif spec["kind"] == "itinerary":
                    check_itinerary(output, spec["rules"])
                else:
                    raise KeyError(f"Unknown checker kind {spec['kind']}")
            checks.append({"check": label, "passed": True})
        except (OSError, ValueError, TypeError, IndexError, UnicodeError) as exc:
            checks.append({"check": label, "passed": False, "error": str(exc)})
        except KeyError as exc:
            # Missing output fields are task failures; malformed specifications
            # are caught by preparation's reference-output validation.
            checks.append({"check": label, "passed": False, "error": f"Missing field: {exc}"})
    return {"case_id": case["case_id"], "variant": variant, "passed": all(c["passed"] for c in checks),
            "passed_checks": sum(c["passed"] for c in checks), "total_checks": len(checks), "checks": checks,
            "scope": case["scope"], "prose_quality_graded": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--variant", choices=("normal", "update", "problem"), required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--base-url", default="http://fixture.invalid")
    parser.add_argument("--snapshots", type=Path)
    parser.add_argument("--requests", type=Path, help="Reviewer-side JSON log from the fixture HTTP server")
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    try:
        case = json.loads(args.case.read_text())
        requests = json.loads(args.requests.read_text()) if args.requests else []
        result = check_case(case, args.variant, args.workspace, args.base_url, snapshots=args.snapshots, requests=requests)
        if args.result:
            args.result.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))
        return 0 if result["passed"] else 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Checker configuration error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
