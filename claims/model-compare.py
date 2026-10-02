#!/usr/bin/env python3
"""
Show Foundry models you have Global Standard quota for, with their price.

Usage:  python3 model-costs.py [region]        (default: swedencentral)

Prices come live from the public Azure Retail Prices API (USD, list price).
Price columns are USD per 1 million tokens, the industry standard unit.
"Blend" = cost of 1M tokens at a typical 3:1 input:output mix, for one-number comparison.
"""
import json
import subprocess
import sys
import urllib.parse
import urllib.request

REGION = sys.argv[1] if len(sys.argv) > 1 else "swedencentral"

# Quota model name -> (input meter, output meter) in the Azure price list.
# The two lists use different naming, so the mapping is maintained by hand.
METERS = {
    "gpt-5-mini": ("GPT 5 Mini Inpt Glbl 1M Tokens", "GPT 5 Mini outpt Glbl 1M Tokens"),
    "gpt4.1-mini": ("gpt 4.1 mini Inp glbl Tokens", "gpt 4.1 mini Outp glbl Tokens"),
    "o4-mini": ("o4-mini 0416 Inp glbl Tokens", "o4-mini 0416 Outp glbl Tokens"),
    "gpt-oss-120b": ("gpt-oss-120B Inp glbl Tokens", "gpt-oss-120B Outp glbl Tokens"),
    "DeepSeek-R1": ("R1 Inp glbl Tokens", "R1 Outp glbl Tokens"),
    "DeepSeek-R1-0528": ("R1 Inp glbl Tokens", "R1 Outp glbl Tokens"),
    "DeepSeek-V3-0324": ("V3-0324 Inp glbl Tokens", "V3-0324 Outp glbl Tokens"),
    "DeepSeek-V3.1": ("V3.1 Inp glbl Tokens", "V3.1 Outp glbl Tokens"),
    "DeepSeek-V3.2": ("V3.2 Inp glbl Tokens", "V3.2 Outp glbl Tokens"),
    "DeepSeek-V3.2-Speciale": ("V3.2 SP Inp glbl Tokens", "V3.2 SP Outp glbl Tokens"),
    "DeepSeek-V4-Flash": ("V4 Flash Inp glbl Tokens", "V4 Flash Outp glbl Tokens"),
    "DeepSeek-V4-Flash-0731": ("V4 Flash 0731 Inp glbl Tokens", "V4 Flash 0731 Outp glbl Tokens"),
    "DeepSeek-V4-Pro": ("V4 Pro Inp glbl Tokens", "V4 Pro Outp glbl Tokens"),
    "MAI-DS-R1": ("MAI-DS-R1 Inp glbl Tokens", "MAI-DS-R1 Outp glbl Tokens"),
    "MAI-Thinking-1": ("MAI-Thinking-1 Inp glbl 1M Tokens", "MAI-Thinking-1 Opt glbl 1M Tokens"),
    "Llama-3.3-70B-Instruct": ("Llama 3.3 70B Inp glbl Tokens", "Llama 3.3 70B Outp glbl Tokens"),
    "Llama-4-Maverick-17B-128E-Instruct-FP8": ("Llama 4 Maverick 17B Inp glbl Tokens", "Llama 4 Maverick 17B Outp glbl Tokens"),
    "Phi-4": ("Phi-4-Input Tokens", "Phi-4-Output Tokens"),
    "Phi-4-mini-instruct": ("Phi-4-Mini-Input Tokens", "Phi-4-Mini-Output Tokens"),
    "Phi-4-mini-reasoning": ("Phi-4-mini-reasoning-Input Tokens", "Phi-4-mini-reasoning-Output Tokens"),
    "Phi-4-reasoning": ("Phi-4-reasoning-Input Tokens", "Phi-4-reasoning-Output Tokens"),
    "Phi-4-multimodal-instruct": ("Phi-4-Mini MM-Input Tokens", "Phi-4-Mini MM-Output Tokens"),
    "Mistral-Large-3": ("Large 3 Inp glbl Tokens", "Large 3 Outp glbl Tokens"),
    "mistral-medium-3-5": ("MM3.5 Inp glbl Tokens", "MM3.5 Outp glbl Tokens"),
    "Codestral-2501": ("Codestral Inp glbl Tokens", "Codestral Outp glbl Tokens"),
    "Cohere-Command-A": ("Command A Inp Glbl Tokens", "Command A Outp Glbl Tokens"),
    "Cohere-command-a-plus-05-2026": ("Command A Plus Inp Glbl 1M Tokens", "Command A Plus Outp Glbl 1M Tokens"),
    "grok-3": ("Grok-3 Inp glbl Tokens", "Grok-3 Outp glbl Tokens"),
    "grok-3-mini": ("Grok-3 Mini Inp glbl Tokens", "Grok-3 Mini Outp glbl Tokens"),
    "grok-4-fast-reasoning": ("Grok4 Fast Inp glbl Tokens", "Grok4 Fast Outp glbl Tokens"),
    "grok-4-fast-non-reasoning": ("Grok4 Fast Inp glbl Tokens", "Grok4 Fast Outp glbl Tokens"),
    "grok-4-1-fast-reasoning": ("Grok 4.1 Inp Glbl Tokens", "Grok 4.1 Outp Glbl Tokens"),
    "grok-4-1-fast-non-reasoning": ("Grok 4.1 Inp Glbl Tokens", "Grok 4.1 Outp Glbl Tokens"),
    "grok-4-20-reasoning": ("Grok 4.2 Inp glbl Tokens", "Grok 4.2 Outp glbl Tokens"),
    "grok-4-20-non-reasoning": ("Grok 4.2 Inp glbl Tokens", "Grok 4.2 Outp glbl Tokens"),
    "grok-4.3": ("4.3 Inp Glbl Tokens", "4.3 Outp Glbl Tokens"),
    "grok-4.6": ("4.6 Inp Glbl Tokens", "4.6 Outp Glbl Tokens"),
    "Kimi-K2-Thinking": ("K2 Thinking Inp glbl Tokens", "K2 Thinking Outp glbl Tokens"),
    "Kimi-K2.5": ("K2.5 Thinking Inp glbl Tokens", "K2.5 Thinking Outp glbl Tokens"),
    "Kimi-K2.6": ("K2.6 Thinking Inp glbl Tokens", "K2.6 Thinking Outp glbl Tokens"),
    "Kimi-K2.7-Code": ("K2.7 Code Inp glbl Tokens", "K2.7 Code Outp glbl Tokens"),
    "text-embedding-3-small": ("text-embedding-3-small-glbl Tokens", None),
    "Embed-V-4-0": ("Embed v4 Txt Glbl Tokens", None),
}


def get_quota():
    out = subprocess.run(
        ["az", "cognitiveservices", "usage", "list", "--location", REGION, "-o", "json"],
        capture_output=True, text=True, check=True,
    ).stdout
    quota = {}
    for u in json.loads(out):
        name = u["name"]["value"]
        if ".GlobalStandard." not in name or u["limit"] <= 0 or "finetune" in name.lower():
            continue
        quota[name.split(".GlobalStandard.", 1)[1]] = (u["currentValue"], u["limit"])
    return quota


def get_prices():
    flt = f"serviceName eq 'Foundry Models' and armRegionName eq '{REGION}' and type eq 'Consumption'"
    url = "https://prices.azure.com/api/retail/prices?$filter=" + urllib.parse.quote(flt)
    prices = {}
    while url:
        data = json.load(urllib.request.urlopen(url))
        for item in data["Items"]:
            per_million = {"1K": 1000, "1M": 1}.get(item["unitOfMeasure"])
            if per_million:
                prices[item["meterName"]] = item["retailPrice"] * per_million
        url = data.get("NextPageLink")
    return prices


def main():
    print(f"Region: {REGION}. Fetching quota and prices...\n")
    quota = get_quota()
    prices = get_prices()

    rows, unpriced = [], []
    for model, (used, limit) in quota.items():
        in_meter, out_meter = METERS.get(model, (None, None))
        p_in = prices.get(in_meter)
        p_out = prices.get(out_meter) if out_meter else 0.0
        if p_in is None or p_out is None:
            unpriced.append(model)
            continue
        blend = (3 * p_in + p_out) / 4
        rows.append((model, used, limit, p_in, p_out if out_meter else None, blend))

    rows.sort(key=lambda r: r[5])
    print(f"{'Model':<40} {'Used':>6} {'Limit':>7} {'In $/1M':>9} {'Out $/1M':>9} {'Blend':>8}")
    print("-" * 84)
    for model, used, limit, p_in, p_out, blend in rows:
        out_txt = f"{p_out:9.2f}" if p_out is not None else f"{'-':>9}"
        print(f"{model:<40} {used:>6g} {limit:>7g} {p_in:9.2f} {out_txt} {blend:8.2f}")

    if unpriced:
        print("\nQuota available but no token price mapped (images, audio, OCR, new models):")
        print("  " + ", ".join(sorted(unpriced)))
    print("\nLimit = thousands of tokens per minute. Prices = USD list price per 1M tokens.")


if __name__ == "__main__":
    main()