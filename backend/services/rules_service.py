import yaml

def load_rules(review_type: str) -> str:
    path = f"rules/{review_type}_rules.yaml"
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    rules_text = ""
    for r in data["rules"]:
        rules_text += f"- [{r['id']}] ({r['severity'].upper()}) {r['rule']}\n"
    return rules_text

def load_raw_rules(review_type: str) -> dict:
    path = f"rules/{review_type}_rules.yaml"
    with open(path, "r") as f:
        return yaml.safe_load(f)

def save_rules(review_type: str, data: dict):
    path = f"rules/{review_type}_rules.yaml"
    with open(path, "w") as f:
        yaml.dump(data, f, allow_unicode=True)
