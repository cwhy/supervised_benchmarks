# CWhy Supervised Learning Benchmark
## Intro
CSLB (CWhy Supervised Learning Benchmark) is my personal benchmark to measure perfomance of supervised learning.
Risen from ashes of cwhy/MLKit(Rip TF1.0x)

Support Python3.8+

## Non Goals
* make a unbiased benchmark for everyone
* measure computational resources of algorithms
* no-friction plugin of new networks
* unsupervised learning (maybe in the long future) or RL
* ImageNet-level large datasets that poor souls can't afford
* super efficient training

## Final Goals
* measure supervised learning as my bias goes
* no nn framework dependency
* very handy to plugin anything Python by wrappers
* support cwhy/anynet input/output configurations
* nice debug messages thoughout the whole experience
* utilize Python to its finest

## Current Goals
* quick and dirty version for testing cwhy/anynet
* types are a must, no array type yet
* dataconfig type won't deal with transformations, only query
* mnist/fashion mnist

## Short Term Goals
* input output validation
* cifar, tabular datasets from UCI and stuff

## Acknowledgement
* Download helper functions are from https://github.com/pytorch/vision
