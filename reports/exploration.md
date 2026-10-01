# Data exploration

Round-trip cost assumed: 0.30% (fee 0.10% + slippage 0.05%, per side, x2).

## Return distribution (1h)

   coin  bars_1h  mean_%  std_%   skew  excess_kurtosis  p01_%  p99_%  ann_vol_%  buy_hold_%
BTCUSDT    25583   0.004  0.502 -0.139           10.072 -1.527  1.470     47.014     191.138
ETHUSDT    25583   0.002  0.690 -0.358           16.668 -2.050  1.941     64.612      47.410
SOLUSDT    25583   0.006  0.925  0.115            8.910 -2.646  2.637     86.616     383.396

## Typical move vs. round-trip cost

   coin interval  median_abs_move_%  mean_abs_move_%  share_bars_abs>round_trip  share_bars_abs>2x_round_trip
BTCUSDT       5m              0.062            0.095                      4.654                         0.675
BTCUSDT       1h              0.211            0.326                     36.563                        14.322
ETHUSDT       5m              0.084            0.128                      8.739                         1.636
ETHUSDT       1h              0.289            0.445                     48.591                        22.832
SOLUSDT       5m              0.122            0.180                     16.963                         3.747
SOLUSDT       1h              0.421            0.623                     62.217                        36.387

## Volatility by hour (UTC), mean |1h return| %

           BTCUSDT  ETHUSDT  SOLUSDT
open_time                           
0            0.320    0.453    0.660
1            0.352    0.497    0.692
2            0.316    0.430    0.626
3            0.274    0.376    0.578
4            0.250    0.340    0.536
5            0.254    0.370    0.542
6            0.262    0.363    0.540
7            0.277    0.379    0.527
8            0.287    0.406    0.589
9            0.267    0.370    0.534
10           0.252    0.352    0.522
11           0.258    0.363    0.516
12           0.296    0.405    0.581
13           0.424    0.556    0.741
14           0.527    0.664    0.865
15           0.486    0.633    0.841
16           0.380    0.516    0.701
17           0.398    0.551    0.736
18           0.359    0.475    0.652
19           0.343    0.458    0.622
20           0.328    0.456    0.613
21           0.311    0.439    0.590
22           0.331    0.453    0.623
23           0.274    0.366    0.525

## Volatility by weekday, mean |1h return| %

     BTCUSDT  ETHUSDT  SOLUSDT
Mon    0.393    0.528    0.696
Tue    0.373    0.489    0.664
Wed    0.361    0.483    0.662
Thu    0.353    0.473    0.655
Fri    0.367    0.485    0.666
Sat    0.189    0.291    0.477
Sun    0.246    0.363    0.540

Charts: `returns_hist_*.png`, `volatility_seasonality.png`, `moves_vs_cost.png`.