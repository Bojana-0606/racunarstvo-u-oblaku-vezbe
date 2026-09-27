import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', required=True)
    parser.add_argument('--target', required=True)
    parser.add_argument('--train-percent', type=int, required=True)
    args = parser.parse_args()

    if not 1 <= args.train_percent <= 99:
        parser.error('--train-percent mora biti između 1 i 99')

    df = pd.read_csv(args.csv)
    df.columns = df.columns.str.strip()
    if args.target not in df.columns:
        parser.error(f'Kolona {args.target!r} ne postoji. Dostupne su: {list(df.columns)}')

    # Svi podaci moraju biti numerički za izabrani regresioni model.
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=[args.target])
    if len(df) < 10:
        parser.error('Potrebno je bar 10 redova sa poznatom ciljnom vrednošću')
    features = [col for col in df.columns if col != args.target]
    if not features:
        parser.error('CSV mora imati makar jednu ulaznu kolonu pored ciljne')
    if df[features].notna().sum().eq(0).any():
        parser.error('Najmanje jedna ulazna kolona je u celosti prazna')

    train, test = train_test_split(
        df, train_size=args.train_percent / 100, random_state=42, shuffle=True
    )
    train, test = train.copy(), test.copy()
    if len(train) < 5 or len(test) < 2:
        parser.error('Izabrani procenat daje premali trening ili test skup')

    means = train[features].mean()
    train[features] = train[features].fillna(means)
    test[features] = test[features].fillna(means)

    # IQR pragovi se uče samo iz treninga; test se ne filtrira.
    q1, q3 = train[features].quantile(.25), train[features].quantile(.75)
    iqr = q3 - q1
    active = iqr > 0
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    outside = train[features].lt(lower) | train[features].gt(upper)
    outlier_rows = outside.loc[:, active].any(axis=1)
    cleaned = train.loc[~outlier_rows].copy()
    if len(cleaned) < 5:
        parser.error('Posle uklanjanja outlier-a ostalo je premalo redova za trening')

    cleaned.to_csv('train_clean.csv', index=False)
    test.to_csv('test_clean.csv', index=False)
    report = {
        'target': args.target,
        'train_percent': args.train_percent,
        'rows_csv_after_missing_target_removal': len(df),
        'rows_train_before_outlier_removal': len(train),
        'rows_outliers_removed_from_train': int(outlier_rows.sum()),
        'rows_train_after_cleaning': len(cleaned),
        'rows_test_untouched_by_outlier_filter': len(test),
        'feature_means_used_for_imputation': means.to_dict(),
    }
    Path('preprocessing_report.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    print(json.dumps({k: v for k, v in report.items() if k != 'feature_means_used_for_imputation'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
