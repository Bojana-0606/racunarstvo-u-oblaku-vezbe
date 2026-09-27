import argparse
import json
from pathlib import Path
from statistics import mean, stdev


def main():
    parser = argparse.ArgumentParser(description='Agregacija metrika po foldovima')
    parser.add_argument('metrics', nargs='+')
    args = parser.parse_args()
    folds = [json.loads(Path(name).read_text(encoding='utf-8')) for name in args.metrics]
    if len(folds) < 2:
        parser.error('Potrebna su najmanje dva folda')
    keys = ['RMSE', 'PRMSE_percent', 'MAE', 'R2']
    summary = {
        'target': folds[0]['target'], 'k': len(folds),
        'PRMSE_definition': folds[0]['PRMSE_definition'],
        'folds': [{
            'fold': index, 'train_rows': item['train_rows'],
            'test_rows': item['test_rows'],
            **{key: item[key] for key in keys}
        } for index, item in enumerate(folds, 1)],
        'mean': {}, 'sample_std': {}
    }
    for key in keys:
        values = [item[key] for item in folds]
        if any(value is None for value in values):
            summary['mean'][key] = None
            summary['sample_std'][key] = None
        else:
            summary['mean'][key] = mean(values)
            summary['sample_std'][key] = stdev(values)
    Path('summary.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    print(json.dumps({'k': len(folds), 'mean': summary['mean']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
