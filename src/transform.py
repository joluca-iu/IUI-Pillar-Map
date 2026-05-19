import ast
import pandas as pd
import os
import json
import math
from datetime import datetime, timezone
from utils.paths import DATA_DIR
import re

_CUTOFF = datetime(2023, 1, 1, tzinfo=timezone.utc)


def _parse_date(val):
    if not val or (isinstance(val, float) and math.isnan(val)):
        return None
    try:
        return datetime.fromisoformat(str(val))
    except ValueError:
        return None


def _should_keep_activity(act):
    start = _parse_date(act.get('startTime'))
    end   = _parse_date(act.get('endTime'))
    if start is None or start >= _CUTOFF:
        return True
    # started before 2023 — only remove if it has also ended
    return end is None or end > datetime.now(timezone.utc)


def _parse_activity_list(raw):
    """Parse a Python-repr list string into its elements without splitting on commas inside names."""
    try:
        val = ast.literal_eval(str(raw))
        if isinstance(val, list):
            return [str(item).strip() for item in val if str(item).strip()]
        return [str(val).strip()] if str(val).strip() else []
    except Exception:
        return [a.strip() for a in re.sub(r"[\[\]']", "", str(raw)).split(',') if a.strip()]


def _sanitize(v):
    """Recursively replace float NaN with None for JSON safety."""
    if isinstance(v, float) and math.isnan(v):
        return None
    if isinstance(v, dict):
        return {k: _sanitize(val) for k, val in v.items()}
    if isinstance(v, list):
        return [_sanitize(val) for val in v]
    return v

def transform_community_partners():
    ##Read data in from raw
    raw_data_dir = DATA_DIR / "raw"

    all_data = []
    # activities_by_name: activity name -> activity dict (deduplicated across programs)
    activities_by_name = {}
    # units_by_activity: lowercase unit name -> {name, url}
    units_by_activity = {}

    for campus in os.listdir(raw_data_dir):
        campus_dir = raw_data_dir / campus
        if not os.path.isdir(campus_dir):
            continue
        for file in os.listdir(campus_dir):
            if file == "activities.csv":
                acts_df = pd.read_csv(campus_dir / file)
                for _, row in acts_df.iterrows():
                    name = row.get('name')
                    if not name or pd.isna(name):
                        continue
                    name = str(name)
                    act = row.to_dict()
                    # Parse pipe-joined list columns back to actual lists
                    for col in ('focuses', 'goal_names'):
                        val = act.get(col)
                        if isinstance(val, str) and val:
                            act[col] = [s.strip() for s in val.split('|') if s.strip()]
                        else:
                            act[col] = []
                    if name not in activities_by_name:
                        activities_by_name[name] = act
                    else:
                        # Same activity fetched under multiple programs — accumulate goal_names
                        existing = set(activities_by_name[name].get('goal_names') or [])
                        incoming = set(act.get('goal_names') or [])
                        activities_by_name[name]['goal_names'] = list(existing | incoming)
            elif file == "units.csv":
                units_df = pd.read_csv(campus_dir / file)
                for _, row in units_df.iterrows():
                    n = row.get('name')
                    if not n or pd.isna(n):
                        continue
                    n = str(n).strip()
                    unit_id = row.get('id')
                    unit_url = (
                        f"https://he.cecollaboratory.com/collaboratory/F27JCV0D2/units/{unit_id}"
                        f"#community_partners/?page=1&perPage=4&sortBy=newest"
                    ) if unit_id and pd.notna(unit_id) else None
                    unit_entry = {
                        'name': n,
                        'url': unit_url
                    }
                    # Build inverted index: each activity name this unit is linked to
                    raw_act_names = row.get('activityName') or ''
                    # activityName may be stored as a Python-repr list string or plain string
                    cleaned = re.sub(r"[\[\]\"']", '', str(raw_act_names))
                    for act_n in (s.strip() for s in cleaned.split(',') if s.strip()):
                        units_by_activity.setdefault(act_n.lower(), []).append(unit_entry)
            elif file.endswith(".csv"):
                all_data.append(pd.read_csv(campus_dir / file))

    # Filter out activities that started before 2023 and have since ended
    activities_by_name = {k: v for k, v in activities_by_name.items() if _should_keep_activity(v)}

    surviving_names = set(activities_by_name.keys())

    # Save filtered activity list for review
    cleaned_data_dir = DATA_DIR / "review"
    os.makedirs(cleaned_data_dir, exist_ok=True)
    pd.DataFrame(list(activities_by_name.values())).to_csv(
        cleaned_data_dir / "activities_date_filtered.csv", index=False
    )

    ##Join all csv together
    combined_df = pd.concat(all_data, ignore_index=True)

    #Combine schools in same campus and aggregate their programs
    combined_df = combined_df.groupby(
        ['name', 'id', 'portal_name'], as_index=False
    ).agg({
        'street': 'first',
        'street2': 'first',
        'zipcode': 'first',
        'city': 'first',
        'state': 'first',
        'county': 'first',
        'country': 'first',
        'latitude': 'first',
        'longitude': 'first',
        'type': 'first',
        'description': 'first',
        'url': 'first',
        'phone': 'first',
        'email': 'first',
        'archived': 'first',
        'status': 'first',
        # Activities — flatten and deduplicate individual names across all grouped rows
        'activityName': lambda x: sorted(set(
            a
            for raw in x.dropna().astype(str)
            for a in _parse_activity_list(raw)
        )),
        'activityCnt':  lambda x: x.dropna().astype(str).nunique(),
        # Roles / contacts
        'role': lambda x: ', '.join(sorted(x.dropna().astype(str).unique())),
        'contactNames': lambda x: ', '.join(sorted(x.dropna().astype(str).unique())),
        'contactEmails': lambda x: ', '.join(sorted(x.dropna().astype(str).unique())),
        # Courses / sections
        'courses': lambda x: ', '.join(sorted(x.dropna().astype(str).unique())),
        'sectionCnt': lambda x: x.dropna().astype(str).nunique(),
        # Units
        'unitNames': lambda x: ', '.join(sorted(x.dropna().astype(str).unique())),
        'unitCnt':  lambda x: x.dropna().astype(str).nunique(),
        'externalId': 'first',
        # Provenance — portal_name is a groupby key, preserved automatically
        'programs': lambda x: sorted(x.dropna().astype(str).unique())
    })

    #Fix externalId formatting
    combined_df['externalId'] = (
        combined_df['externalId']
        .astype(str)
        .str.replace(r'\.0$', '', regex=True)
        .str.pad(width=4, side='right', fillchar='0')
    )

    #Save partners with no real location before dropping them
    cleaned_data_dir = DATA_DIR / "review"
    os.makedirs(cleaned_data_dir, exist_ok=True)

    # Orgs with null lat/lon — truly missing coordinates
    no_latlon_mask = combined_df[['latitude', 'longitude']].isnull().any(axis=1)
    # Orgs where the API auto-generated coordinates (no street AND no city = no real address)
    no_address_mask = combined_df['street'].isna() & combined_df['city'].isna()
    no_location = combined_df[no_latlon_mask | no_address_mask]
    if not no_location.empty:
        no_location.to_csv(cleaned_data_dir / "no_location_partners.csv", index=False)

    #Drop rows with no real location
    combined_df = combined_df[~(no_latlon_mask | no_address_mask)]
    combined_df = combined_df.dropna(subset=['latitude', 'longitude', 'portal_name', 'name'])
    #Replace remaining NaNs with None for JSON compatibility
    combined_df = combined_df.where(pd.notnull(combined_df), None)
    
    combined_df = combined_df.rename(columns={"latitude": "lat", "longitude": "lon"})

    # Drop partners whose every activity was filtered out by the date rule
    combined_df = combined_df[
        combined_df['activityName'].apply(
            lambda names: any(n in surviving_names for n in (names if isinstance(names, list) else []))
        )
    ]

    # Build inverted index: activity name → [{id, name}] for all located orgs
    activity_partners = {}
    for _, row in combined_df.iterrows():
        act_names = row['activityName'] or []
        if not isinstance(act_names, list):
            act_names = [a.strip() for a in str(act_names).split(',') if a.strip()]
        org = {'id': row['id'], 'name': row['name']}
        for act_name in act_names:
            activity_partners.setdefault(act_name, []).append(org)

    # Attach community_partners and unit_links to each activity
    for act_name, act in activities_by_name.items():
        act['community_partners'] = activity_partners.get(act_name, [])
        # Look up which units are linked to this activity by name (inverted index)
        act['unit_links'] = units_by_activity.get(act_name.lower(), [])

    ###Combine entites with same lat/lon into single entry###
    #In the future once IDOE codes are imported to Colab, we can use those to distinguish public schools vs corporations vs charters

    def row_to_entity(row):
        entity = {k: _sanitize(row[k]) for k in combined_df.columns.drop(['lat', 'lon'])}
        # Resolve activityName strings to full activity objects via name lookup
        act_names = entity.get('activityName') or []
        if isinstance(act_names, str):
            act_names = [a.strip() for a in act_names.split(',') if a.strip()]
        entity['activities'] = [
            _sanitize(activities_by_name[n]) for n in act_names if n in activities_by_name
        ]
        return entity
    
    # minimal columns for the map
    cols = ["externalId", "portal_name", "name", "lat", "lon", "programs", "activityName"]
    temp_df = combined_df[cols].copy() #Temp df to create grouped_df
    temp_df['entity'] = combined_df.apply(row_to_entity, axis=1)

    #Group by lat/lon
    grouped_df = temp_df.groupby(['lat', 'lon'])['entity'].apply(list).reset_index()
    #Convert to json
    grouped_json = grouped_df.to_dict(orient='records')

    ##Write combined data to cleaned folder
    #Community partners where duplicate schools on same campus are combined
    combined_df.to_csv(cleaned_data_dir / "combined_community_partners_by_campus.csv", index=False)

    return grouped_json