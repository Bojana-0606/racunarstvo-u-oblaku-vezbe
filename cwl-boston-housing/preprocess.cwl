cwlVersion: v1.2
class: CommandLineTool
requirements:
  DockerRequirement:
    dockerPull: bojana0606/cwl-boston-preprocess:1.0
baseCommand: [python, /app/preprocess.py]
inputs:
  csv:
    type: File
    inputBinding: {prefix: --csv, position: 1}
  target:
    type: string
    inputBinding: {prefix: --target, position: 2}
  train_percent:
    type: int
    inputBinding: {prefix: --train-percent, position: 3}
outputs:
  train:
    type: File
    outputBinding: {glob: train_clean.csv}
  test:
    type: File
    outputBinding: {glob: test_clean.csv}
  report:
    type: File
    outputBinding: {glob: preprocessing_report.json}
