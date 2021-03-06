

#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from pyspark.sql import SparkSession
from pyspark.ml.recommendation import ALS
from pyspark.mllib.evaluation import RankingMetrics
from pyspark.sql.functions import col, expr
import numpy as np
import itertools
def main(spark, train_file,val_file, model_file):
    df_train = spark.read.parquet(train_file)
    df_val = spark.read.parquet(val_file)
    print(df_train.count())
    print(df_val.count())
    als = ALS(implicitPrefs=True,userCol="userIndex", itemCol="trackIndex", ratingCol="count", coldStartStrategy="drop")
    ranks = [10,20,40]
    reg_params = [0.001,0.01,0.1]
    alphas = [1,20,40]
    max_result = 0.0
    best_rank = 0
    best_alpha = 0
    best_regparam = 0
    k=500
    val_user = df_val.select('userIndex').distinct()
    for rank, reg_param, alpha in itertools.product(ranks, reg_params, alphas):
        als.setRank(rank).setRegParam(reg_param).setAlpha(alpha)
        model = als.fit(df_train)
        rec = model.recommendForUserSubset(val_user,500)
        predictions = model.transform(df_val)
        actual = df_val.groupBy("userIndex").agg(expr("collect_set(trackIndex) as tracks"))
        pred= rec.select('userIndex','recommendations.trackIndex')
        a=pred.join(actual,['userIndex']).select('trackIndex','tracks')
        metrics = RankingMetrics(a.rdd)
        result = metrics.meanAveragePrecision
        print('For rank %s, for alpha %s, for reg_param %s, the MAP is %s' % (rank, alpha, reg_param, result))
        if result > max_result:
            max_result = result
            best_rank = rank
            best_alpha = alpha
            best_regparam = reg_param
    best = als.setRank(best_rank).setAlpha(best_alpha).setRegParam(best_regparam)
    best_model_ = best.fit(df_train)
    best_model_.save(model_file)
if __name__ == "__main__":

    # Create the spark session object
    spark = SparkSession.builder.appName('als').getOrCreate()

    # Get the filename from the command line
    train_file = sys.argv[1]
    val_file = sys.argv[2]
    model_file = sys.argv[3]

    # Call our main routine
    main(spark, train_file,val_file, model_file)
