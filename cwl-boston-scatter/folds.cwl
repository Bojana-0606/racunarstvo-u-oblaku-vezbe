cwlVersion: v1.2
class: CommandLineTool
requirements:
  DockerRequirement:
    dockerPull: bojana0606/cwl-boston-folds:1.0
baseCommand: [python, /app/folds.py]
inputs:
  csv:
    type: File
    inputBinding: {prefix: --csv, position: 1}
  target:
    type: string
    inputBinding: {prefix: --target, position: 2}
  k:
    type: int
    inputBinding: {prefix: --k, position: 3}
outputs:
  train:
    type: File[]
    outputBinding: {glob: 'fold_*_train.csv'}
  test:
    type: File[]
    outputBinding: {glob: 'fold_*_test.csv'}
  report:
    type: File
    outputBinding: {glob: folds_report.json}
