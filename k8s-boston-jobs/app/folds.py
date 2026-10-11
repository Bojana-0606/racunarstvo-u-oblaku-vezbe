import argparse
import json
from pathlib import Path

import pandas as pd
from sklearn.model_selection import KFold


def main():
    parser = argparse.ArgumentParser(description='Priprema k trening/test parova')
    parser.add_argument('--csv', required=True)
    parser.add_argument('--target', required=True)
    parser.add_argument('--k', type=int, required=True)
    args = parser.parse_args()

    df = pd.read_csv(args.csv)
    df.columns = df.columns.str.strip()
    if args.target not in df.columns:
        parser.error(f'Ciljna kolona {args.target!r} ne postoji')
    df = df.apply(pd.to_numeric, errors='coerce').dropna(subset=[args.target])
    if not 2 <= args.k <= len(df):
        parser.error(f'k mora biti od 2 do {len(df)}')
    features = [column for column in df if column != args.target]
    if not features:
        parser.error('Potreban je makar jedan ulazni atribut')

    report = {'target': args.target, 'k': args.k, 'rows': len(df), 'folds': []}
    for number, (train_index, test_index) in enumerate(
        KFold(n_splits=args.k, shuffle=True, random_state=42).split(df), start=1
    ):
        train = df.iloc[train_index].copy()
        test = df.iloc[test_index].copy()
        means = train[features].mean()
        if means.isna().any():
            parser.error(f'Fold {number}: ulazna kolona je potpuno prazna u treningu')
        train[features] = train[features].fillna(means)
        test[features] = test[features].fillna(means)

        q1, q3 = train[features].quantile(.25), train[features].quantile(.75)
        iqr = q3 - q1
        outside = train[features].lt(q1 - 1.5 * iqr) | train[features].gt(q3 + 1.5 * iqr)
        outliers = outside.loc[:, iqr > 0].any(axis=1)
        cleaned = train.loc[~outliers].copy()
        if len(cleaned) < 5 or len(test) < 2:
            parser.error(f'Fold {number}: trening ili test skup je premali')
        name = f'fold_{number:04d}'
        cleaned.to_csv(f'{name}_train.csv', index=False)
        test.to_csv(f'{name}_test.csv', index=False)
        report['folds'].append({
            'fold': number, 'train_before_outliers': len(train),
            'train_after_outliers': len(cleaned), 'outliers_removed': int(outliers.sum()),
            'test_rows': len(test)
        })
    Path('folds_report.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    print(json.dumps({'k': args.k, 'rows': len(df), 'folds_created': len(report['folds'])}))


if __name__ == '__main__':
    main()
