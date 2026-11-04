-- Logement (généré par gen_logement.py) : maisons, panneaux de vente, catalogue de meubles, décoration retirée des maisons
CREATE TABLE IF NOT EXISTS `custom_maison_lieu` (`id` INT UNSIGNED NOT NULL, `ville` VARCHAR(64) NOT NULL, `map` SMALLINT UNSIGNED NOT NULL, `x` FLOAT NOT NULL, `y` FLOAT NOT NULL, `z` FLOAT NOT NULL, `o` FLOAT NOT NULL, `x0` FLOAT NOT NULL, `y0` FLOAT NOT NULL, `z0` FLOAT NOT NULL, `x1` FLOAT NOT NULL, `y1` FLOAT NOT NULL, `z1` FLOAT NOT NULL, `taille` VARCHAR(16) NOT NULL, `prix` INT UNSIGNED NOT NULL, PRIMARY KEY (`id`)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
DELETE FROM `custom_maison_lieu`;
INSERT INTO `custom_maison_lieu` VALUES
(1, 'Hurlevent', 0, -8709.76, 1053.40, 97.92, 0.000, -8729.76, 1033.40, 95.92, -8689.76, 1073.40, 107.75, 'grande', 4000000),
(2, 'Hurlevent', 0, -8540.54, 546.03, 104.70, 0.000, -8557.10, 533.41, 102.70, -8523.97, 566.03, 109.85, 'grande', 4000000),
(3, 'Hurlevent', 0, -8741.36, 656.39, 107.06, 0.000, -8760.50, 641.27, 105.06, -8729.96, 671.50, 112.21, 'grande', 4000000),
(4, 'Hurlevent', 0, -8826.56, 1134.01, 100.31, 0.000, -8841.33, 1119.20, 98.31, -8811.79, 1148.82, 105.46, 'grande', 4000000),
(5, 'Hurlevent', 0, -8774.27, 1002.09, 106.91, 0.000, -8788.50, 987.81, 104.91, -8760.04, 1016.36, 112.06, 'grande', 4000000),
(6, 'Hurlevent', 0, -8820.39, 1089.36, 97.96, 0.000, -8830.23, 1078.88, 95.96, -8808.07, 1102.21, 101.96, 'moyenne', 1500000),
(7, 'Hurlevent', 0, -8858.28, 859.60, 101.58, 0.000, -8869.47, 848.23, 99.58, -8847.08, 870.96, 106.73, 'moyenne', 1500000),
(8, 'Forgefer', 0, -4804.10, -1005.66, 504.45, 0.000, -4822.21, -1023.51, 502.45, -4785.99, -987.80, 517.06, 'grande', 4000000),
(9, 'Forgefer', 0, -4663.46, -1162.45, 505.81, 0.000, -4681.25, -1180.07, 503.81, -4645.67, -1144.84, 517.73, 'grande', 4000000),
(10, 'Forgefer', 0, -4897.34, -1084.86, 504.74, 0.000, -4914.32, -1101.48, 502.74, -4880.36, -1068.24, 515.32, 'grande', 4000000),
(11, 'Hurlevent', 0, -8823.59, 600.50, 95.58, 2.559, -8838.94, 584.94, 95.51, -8811.86, 612.17, 102.69, 'moyenne', 1500000),
(12, 'Hurlevent', 0, -8849.25, 568.93, 94.69, 2.388, -8865.60, 556.34, 94.64, -8841.02, 581.30, 108.27, 'moyenne', 1500000),
(13, 'Hurlevent', 0, -8892.58, 613.36, 95.26, 5.314, -8900.57, 599.23, 95.21, -8877.08, 625.19, 102.37, 'moyenne', 1500000),
(14, 'Hurlevent', 0, -8777.42, 638.41, 97.22, 3.366, -8789.79, 626.85, 97.11, -8761.74, 654.87, 105.72, 'moyenne', 1500000),
(15, 'Hurlevent', 0, -8795.18, 703.63, 102.28, 4.587, -8808.21, 685.90, 102.23, -8777.53, 716.62, 115.87, 'grande', 4000000),
(16, 'Hurlevent', 0, -8825.20, 515.00, 98.68, 5.436, -8832.29, 504.44, 98.65, -8809.36, 527.89, 112.26, 'moyenne', 1500000),
(17, 'Hurlevent', 0, -8711.65, 383.01, 103.73, 0.960, -8722.91, 368.06, 103.61, -8695.29, 395.63, 112.22, 'moyenne', 1500000),
(18, 'Hurlevent', 0, -8663.33, 384.82, 104.27, 2.283, -8674.00, 377.38, 104.24, -8651.07, 400.83, 117.85, 'moyenne', 1500000),
(19, 'Hurlevent', 0, -8656.82, 451.09, 104.25, 5.313, -8665.80, 438.78, 104.18, -8642.87, 462.23, 117.83, 'moyenne', 1500000),
(20, 'Hurlevent', 0, -8663.09, 516.75, 101.28, 4.410, -8676.87, 497.49, 101.24, -8646.19, 528.10, 114.86, 'grande', 4000000),
(21, 'Hurlevent', 0, -8659.99, 478.92, 101.20, 2.526, -8674.57, 466.68, 101.09, -8652.18, 489.41, 108.32, 'moyenne', 1500000),
(22, 'Hurlevent', 0, -8663.64, 431.62, 100.91, 2.063, -8676.99, 419.48, 100.87, -8654.51, 442.32, 108.02, 'moyenne', 1500000),
(23, 'Hurlevent', 0, -8466.14, 504.93, 99.78, 2.123, -8473.14, 497.93, 97.78, -8459.14, 511.93, 107.78, 'petite', 500000),
(24, 'Hurlevent', 0, -8415.21, 543.59, 95.45, 2.348, -8428.25, 535.26, 95.41, -8404.00, 560.33, 102.56, 'moyenne', 1500000),
(25, 'Hurlevent', 0, -8391.25, 690.03, 95.27, 3.808, -8402.66, 673.22, 95.24, -8379.21, 696.16, 108.86, 'moyenne', 1500000),
(26, 'Hurlevent', 0, -8432.69, 690.30, 96.32, 5.219, -8440.40, 675.76, 96.28, -8416.14, 700.83, 103.43, 'moyenne', 1500000),
(27, 'Hurlevent', 0, -8551.85, 596.98, 104.60, 2.262, -8569.06, 585.08, 104.55, -8545.98, 608.68, 118.18, 'moyenne', 1500000),
(28, 'Hurlevent', 0, -8647.60, 680.62, 101.86, 3.546, -8659.92, 664.67, 101.72, -8636.33, 687.75, 115.34, 'moyenne', 1500000),
(29, 'Hurlevent', 0, -8696.34, 845.70, 98.69, 2.207, -8710.89, 832.46, 98.66, -8687.95, 855.91, 112.27, 'moyenne', 1500000),
(30, 'Hurlevent', 0, -8628.72, 882.22, 103.18, 5.408, -8637.76, 871.11, 103.12, -8614.92, 894.40, 110.30, 'moyenne', 1500000),
(31, 'Hurlevent', 0, -8672.82, 792.27, 101.72, 5.357, -8680.84, 781.74, 101.60, -8658.45, 804.46, 108.83, 'moyenne', 1500000),
(32, 'Hurlevent', 0, -8564.08, 710.60, 103.52, 2.125, -8577.98, 697.37, 103.46, -8555.13, 720.66, 110.64, 'moyenne', 1500000),
(33, 'Hurlevent', 0, -8549.71, 726.16, 101.72, 2.169, -8566.80, 714.24, 101.68, -8542.54, 739.30, 108.83, 'moyenne', 1500000),
(34, 'Hurlevent', 0, -8727.04, 1173.39, 98.34, 4.328, -8734.04, 1166.39, 96.34, -8720.04, 1180.39, 106.34, 'petite', 500000),
(35, 'Hurlevent', 0, -8844.18, 1083.05, 95.21, 0.198, -8851.18, 1076.05, 93.21, -8837.18, 1090.05, 103.21, 'petite', 500000),
(36, 'Hurlevent', 0, -8856.27, 822.12, 98.32, 0.711, -8871.37, 813.19, 98.29, -8844.73, 838.66, 111.90, 'moyenne', 1500000),
(37, 'Hurlevent', 0, -8869.65, 803.37, 97.42, 2.691, -8885.71, 786.39, 97.36, -8855.73, 816.44, 111.00, 'grande', 4000000),
(38, 'Hurlevent', 0, -8940.90, 894.65, 108.10, 3.875, -8957.46, 883.53, 108.07, -8932.04, 908.73, 115.22, 'moyenne', 1500000),
(39, 'Hurlevent', 0, -8992.98, 939.56, 117.10, 2.672, -9007.43, 927.01, 117.05, -8978.13, 956.39, 124.21, 'grande', 4000000),
(40, 'Hurlevent', 0, -8887.92, 976.52, 124.36, 3.284, -8900.68, 965.14, 124.32, -8870.23, 995.55, 131.47, 'grande', 4000000),
(41, 'Hurlevent', 0, -8965.05, 814.68, 109.45, 2.414, -8976.66, 804.41, 109.41, -8953.64, 827.73, 116.56, 'moyenne', 1500000),
(42, 'Hurlevent', 0, -8887.96, 681.29, 100.08, 1.938, -8900.27, 669.37, 100.02, -8877.06, 692.78, 107.20, 'moyenne', 1500000),
(43, 'Hurlevent', 0, -8771.05, 713.65, 99.53, 0.693, -8783.19, 705.40, 99.50, -8758.70, 729.35, 113.12, 'moyenne', 1500000),
(44, 'Hurlevent', 0, -8869.17, 675.93, 97.90, 5.249, -8877.51, 662.64, 97.87, -8852.16, 688.64, 105.02, 'moyenne', 1500000),
(45, 'Forgefer', 0, -4675.69, -861.76, 503.89, 4.932, -4694.89, -881.76, 503.86, -4659.53, -849.21, 517.78, 'grande', 4000000),
(46, 'Forgefer', 0, -4652.49, -890.03, 508.86, 3.646, -4670.18, -904.60, 504.86, -4644.17, -877.81, 514.89, 'moyenne', 1500000),
(47, 'Forgefer', 0, -4712.99, -877.95, 501.96, 5.751, -4729.78, -892.74, 501.93, -4694.80, -858.39, 514.49, 'grande', 4000000),
(48, 'Forgefer', 0, -4713.53, -961.89, 505.29, 1.083, -4729.56, -971.32, 505.26, -4701.64, -944.11, 517.88, 'moyenne', 1500000),
(49, 'Forgefer', 0, -4576.64, -996.48, 504.16, 3.343, -4591.19, -1007.13, 503.63, -4565.74, -982.02, 516.50, 'moyenne', 1500000),
(50, 'Forgefer', 0, -4595.00, -1022.13, 505.29, 1.852, -4613.72, -1036.86, 505.26, -4583.77, -1006.62, 517.88, 'grande', 4000000),
(51, 'Forgefer', 0, -4599.49, -1072.07, 503.59, 2.827, -4619.49, -1092.07, 503.56, -4585.94, -1056.66, 517.48, 'grande', 4000000),
(52, 'Forgefer', 0, -4706.76, -1176.38, 505.27, 5.585, -4726.76, -1196.38, 501.67, -4687.25, -1156.38, 520.27, 'grande', 4000000),
(53, 'Forgefer', 0, -4753.38, -1216.95, 501.93, 4.651, -4768.10, -1229.84, 501.90, -4737.55, -1199.82, 516.51, 'grande', 4000000),
(54, 'Forgefer', 0, -4967.46, -1281.93, 501.97, 0.065, -4985.03, -1300.99, 501.92, -4950.43, -1266.49, 516.55, 'grande', 4000000),
(55, 'Forgefer', 0, -5054.16, -1169.65, 503.68, 0.282, -5066.99, -1183.04, 503.65, -5041.54, -1157.93, 516.52, 'moyenne', 1500000),
(56, 'Forgefer', 0, -5036.81, -1142.72, 505.29, 5.061, -5048.96, -1158.44, 505.26, -5016.81, -1122.72, 517.90, 'grande', 4000000),
(57, 'Forgefer', 0, -4905.84, -1179.28, 503.82, 2.797, -4925.84, -1193.08, 503.79, -4890.03, -1159.28, 517.71, 'grande', 4000000),
(58, 'Forgefer', 0, -5029.55, -1129.54, 505.31, 0.010, -5048.96, -1149.54, 505.26, -5012.99, -1111.80, 517.90, 'grande', 4000000),
(59, 'Forgefer', 0, -4977.48, -1116.34, 503.69, 3.045, -4988.88, -1126.81, 503.66, -4962.83, -1101.06, 516.52, 'moyenne', 1500000),
(60, 'Forgefer', 0, -4962.38, -1035.63, 505.26, 2.680, -4979.41, -1052.71, 503.84, -4944.10, -1015.63, 517.85, 'grande', 4000000),
(61, 'Forgefer', 0, -5032.08, -1016.16, 508.88, 6.129, -5044.03, -1031.49, 504.88, -5012.37, -1000.18, 514.90, 'grande', 4000000),
(62, 'Forgefer', 0, -5024.42, -995.42, 503.88, 0.002, -5034.72, -1014.73, 503.85, -5004.42, -978.02, 517.77, 'grande', 4000000),
(63, 'Forgefer', 0, -4922.55, -1004.80, 502.00, 0.556, -4931.37, -1016.86, 501.97, -4904.46, -990.64, 513.20, 'moyenne', 1500000),
(64, 'Forgefer', 0, -4876.83, -972.68, 505.07, 1.998, -4896.83, -992.68, 503.91, -4860.91, -955.38, 519.47, 'grande', 4000000),
(65, 'Forgefer', 0, -4831.46, -922.71, 502.22, 1.953, -4847.27, -941.84, 502.19, -4815.60, -908.84, 514.76, 'grande', 4000000),
(66, 'Forgefer', 0, -4771.38, -925.65, 503.69, 1.120, -4782.88, -940.38, 503.66, -4755.92, -913.32, 516.52, 'moyenne', 1500000),
(67, 'Forgefer', 0, -4693.78, -1005.00, 502.21, 4.826, -4701.63, -1020.19, 502.18, -4673.78, -992.54, 514.90, 'moyenne', 1500000),
(68, 'Forgefer', 0, -4737.69, -1010.38, 503.66, 4.370, -4749.97, -1023.47, 503.63, -4722.78, -996.09, 516.50, 'moyenne', 1500000),
(69, 'Forgefer', 0, -4710.98, -1080.84, 502.77, 3.274, -4721.83, -1091.67, 502.74, -4699.99, -1069.87, 509.03, 'moyenne', 1500000),
(70, 'Forgefer', 0, -4704.53, -1114.33, 504.44, 2.744, -4724.53, -1134.33, 504.41, -4689.98, -1094.62, 518.34, 'grande', 4000000),
(71, 'Forgefer', 0, -4722.31, -1152.28, 502.45, 2.696, -4731.67, -1163.34, 502.42, -4710.14, -1141.74, 508.71, 'moyenne', 1500000),
(72, 'Forgefer', 0, -4772.23, -1188.43, 502.73, 0.316, -4779.80, -1202.59, 502.70, -4752.23, -1175.51, 515.42, 'moyenne', 1500000),
(73, 'Forgefer', 0, -4835.97, -1181.60, 502.47, 6.125, -4851.17, -1201.60, 502.44, -4815.97, -1169.45, 515.00, 'grande', 4000000),
(74, 'Forgefer', 0, -4857.60, -1173.23, 504.18, 4.004, -4868.94, -1185.83, 504.15, -4845.83, -1162.92, 517.02, 'moyenne', 1500000),
(75, 'Pitons-du-Tonnerre', 1, -1249.15, 152.78, 133.55, 4.940, -1264.04, 137.49, 132.51, -1232.63, 170.43, 148.55, 'grande', 4000000),
(76, 'Pitons-du-Tonnerre', 1, -1243.43, 42.87, 127.09, 0.537, -1263.43, 22.87, 127.15, -1242.45, 42.04, 142.09, 'moyenne', 1500000),
(77, 'Pitons-du-Tonnerre', 1, -1289.42, 75.72, 128.67, 4.173, -1296.42, 68.72, 126.67, -1282.42, 82.72, 136.67, 'petite', 500000),
(78, 'Pitons-du-Tonnerre', 1, -1265.38, 142.02, 132.59, 1.720, -1272.38, 135.02, 130.59, -1258.38, 149.02, 140.59, 'petite', 500000),
(79, 'Pitons-du-Tonnerre', 1, -1375.06, -100.22, 158.94, 2.945, -1382.06, -107.22, 156.94, -1368.06, -93.22, 166.94, 'petite', 500000),
(80, 'Darnassus', 1, 9667.84, 2379.49, 1337.31, 2.726, 9660.84, 2372.49, 1335.31, 9674.84, 2386.49, 1345.31, 'petite', 500000),
(81, 'Darnassus', 1, 9699.11, 2226.17, 1330.01, 0.978, 9687.38, 2212.79, 1329.94, 9712.32, 2238.18, 1336.32, 'moyenne', 1500000),
(82, 'Darnassus', 1, 9845.05, 2183.47, 1329.98, 5.011, 9834.84, 2174.74, 1329.93, 9853.97, 2194.65, 1336.32, 'moyenne', 1500000),
(83, 'Darnassus', 1, 9886.79, 2320.86, 1327.96, 0.707, 9879.79, 2313.86, 1325.96, 9893.79, 2327.86, 1335.96, 'petite', 500000),
(84, 'Darnassus', 1, 10138.30, 2215.34, 1329.98, 5.337, 10125.59, 2204.15, 1329.94, 10150.35, 2229.05, 1336.32, 'moyenne', 1500000),
(85, 'Darnassus', 1, 10217.30, 2337.25, 1330.00, 6.272, 10205.33, 2328.53, 1329.94, 10225.80, 2348.23, 1336.32, 'moyenne', 1500000),
(86, 'Orgrimmar', 1, 1588.34, -4470.34, 7.67, 4.652, 1572.99, -4490.34, 6.73, 1608.34, -4450.34, 14.93, 'grande', 4000000),
(87, 'Orgrimmar', 1, 1691.14, -4410.77, 21.68, 3.721, 1675.45, -4430.77, 21.53, 1711.14, -4395.00, 28.82, 'grande', 4000000),
(88, 'Orgrimmar', 1, 1742.91, -4317.99, 33.37, 3.779, 1725.46, -4335.30, 33.02, 1762.91, -4297.99, 44.87, 'grande', 4000000),
(89, 'Orgrimmar', 1, 1576.22, -4291.77, 25.92, 1.035, 1556.42, -4309.09, 25.66, 1592.70, -4272.94, 37.52, 'grande', 4000000),
(90, 'Orgrimmar', 1, 1518.14, -4354.92, 18.66, 3.146, 1500.67, -4372.73, 18.44, 1536.49, -4336.55, 30.30, 'grande', 4000000),
(91, 'Orgrimmar', 1, 1839.44, -4469.49, 47.45, 1.441, 1819.44, -4488.24, 47.33, 1855.98, -4449.49, 54.62, 'grande', 4000000),
(92, 'Orgrimmar', 1, 1902.71, -4456.58, 53.20, 5.438, 1890.31, -4471.00, 53.17, 1918.02, -4442.77, 61.20, 'moyenne', 1500000),
(93, 'Orgrimmar', 1, 1929.32, -4514.83, 29.06, 4.592, 1916.95, -4531.26, 29.03, 1944.84, -4502.96, 37.07, 'moyenne', 1500000),
(94, 'Orgrimmar', 1, 1802.62, -4567.00, 22.78, 1.389, 1782.62, -4587.00, 22.75, 1822.62, -4547.00, 34.27, 'grande', 4000000),
(95, 'Orgrimmar', 1, 1880.12, -4706.55, 39.28, 4.184, 1860.12, -4726.55, 39.19, 1898.71, -4690.03, 46.48, 'grande', 4000000),
(96, 'Orgrimmar', 1, 1908.86, -4783.06, 36.18, 1.285, 1891.54, -4800.90, 35.29, 1928.86, -4763.06, 43.49, 'grande', 4000000),
(97, 'Orgrimmar', 1, 2026.97, -4704.65, 26.80, 5.639, 2013.74, -4719.14, 26.78, 2041.80, -4691.21, 34.81, 'moyenne', 1500000),
(98, 'Orgrimmar', 1, 2052.65, -4837.49, 24.35, 4.150, 2045.65, -4844.49, 22.35, 2059.65, -4830.49, 32.35, 'petite', 500000),
(99, 'Orgrimmar', 1, 2028.79, -4636.79, 29.55, 1.039, 2008.79, -4654.68, 29.53, 2045.48, -4617.84, 42.73, 'grande', 4000000),
(100, 'Orgrimmar', 1, 1891.98, -4321.71, 23.17, 5.913, 1871.98, -4341.71, 22.72, 1908.85, -4303.80, 31.19, 'grande', 4000000),
(101, 'Orgrimmar', 1, 1783.89, -4205.54, 40.01, 4.430, 1765.23, -4223.90, 39.98, 1802.83, -4186.63, 53.18, 'grande', 4000000),
(102, 'Orgrimmar', 1, 1748.24, -4323.04, 5.91, 3.879, 1741.24, -4330.04, 3.91, 1755.24, -4316.04, 13.91, 'petite', 500000),
(103, 'Orgrimmar', 1, 1810.69, -4276.08, 7.11, 0.687, 1803.69, -4283.08, 5.11, 1817.69, -4269.08, 15.11, 'petite', 500000),
(104, 'Orgrimmar', 1, 1773.57, -4282.12, 7.73, 2.173, 1766.57, -4289.12, 5.73, 1780.57, -4275.12, 15.73, 'petite', 500000),
(105, 'Orgrimmar', 1, 1828.06, -4298.16, -12.40, 3.094, 1821.06, -4305.16, -14.40, 1835.06, -4291.16, -4.40, 'petite', 500000),
(106, 'Orgrimmar', 1, 1840.92, -4321.86, -15.70, 0.830, 1833.92, -4328.86, -17.70, 1847.92, -4314.86, -7.70, 'petite', 500000),
(107, 'Orgrimmar', 1, 1805.41, -4371.72, -17.48, 1.367, 1798.41, -4378.72, -19.48, 1812.41, -4364.72, -9.48, 'petite', 500000),
(108, 'Orgrimmar', 1, 1766.73, -4367.56, -16.02, 1.990, 1759.73, -4374.56, -18.02, 1773.73, -4360.56, -8.02, 'petite', 500000),
(109, 'Orgrimmar', 1, 1579.46, -4096.71, 36.24, 5.080, 1559.46, -4114.80, 35.90, 1597.70, -4076.80, 46.77, 'grande', 4000000),
(110, 'Orgrimmar', 1, 1781.53, -3994.25, 53.16, 0.044, 1768.02, -4007.61, 53.14, 1795.69, -3979.88, 61.17, 'moyenne', 1500000),
(111, 'Fossoyeuse', 0, 1633.90, 202.02, -43.10, 2.287, 1619.71, 193.86, -43.15, 1640.47, 214.97, -28.10, 'moyenne', 1500000),
(112, 'Fossoyeuse', 0, 1572.20, 190.16, -43.10, 4.277, 1566.70, 182.34, -43.13, 1585.67, 204.47, -28.96, 'moyenne', 1500000),
(113, 'Fossoyeuse', 0, 1557.85, 203.92, -43.10, 0.432, 1550.31, 194.47, -43.14, 1571.07, 215.58, -28.10, 'moyenne', 1500000),
(114, 'Fossoyeuse', 0, 1546.29, 260.39, -43.10, 3.220, 1538.08, 251.35, -43.14, 1560.38, 270.58, -28.93, 'moyenne', 1500000),
(115, 'Fossoyeuse', 0, 1645.13, 261.49, -43.10, 3.502, 1631.38, 250.53, -43.13, 1653.68, 269.77, -28.93, 'moyenne', 1500000),
(116, 'Fossoyeuse', 0, 1631.46, 277.55, -43.10, 0.579, 1620.33, 265.07, -43.13, 1641.09, 286.18, -28.10, 'moyenne', 1500000),
(117, 'Comté-de-l''Or', 0, -9377.76, -72.06, 64.44, 1.173, -9386.08, -83.00, 64.37, -9365.35, -56.51, 68.89, 'moyenne', 1500000),
(118, 'Brill', 0, 2261.50, 344.54, 36.02, 5.959, 2251.70, 336.70, 35.96, 2270.33, 354.88, 45.18, 'moyenne', 1500000),
(119, 'Kharanos', 0, -5504.13, -703.04, 393.16, 1.115, -5515.10, -714.67, 391.72, -5489.34, -686.87, 399.47, 'moyenne', 1500000),
(120, 'Kharanos', 0, -5533.85, -667.86, 393.33, 0.673, -5542.21, -678.02, 392.40, -5513.85, -651.29, 405.58, 'moyenne', 1500000),
(121, 'Dolanaar', 1, 9774.26, 879.48, 1297.70, 1.365, 9761.17, 870.06, 1297.27, 9781.61, 884.88, 1306.40, 'moyenne', 1500000),
(122, 'Sabot-de-Sang', 1, -2184.78, -414.83, -4.50, 3.972, -2191.78, -421.83, -6.50, -2177.78, -407.83, 3.50, 'petite', 500000),
(123, 'Sabot-de-Sang', 1, -2344.15, -310.87, -9.38, 2.558, -2351.15, -317.87, -11.38, -2337.15, -303.87, -1.38, 'petite', 500000);
CREATE TABLE IF NOT EXISTS `custom_maison_catalogue` (`entry` INT UNSIGNED NOT NULL, `num` SMALLINT UNSIGNED NOT NULL, `nom` VARCHAR(64) NOT NULL, PRIMARY KEY (`entry`)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
DELETE FROM `custom_maison_catalogue`;
INSERT INTO `custom_maison_catalogue` VALUES
(990600, 1, 'Chaise simple'),
(990601, 2, 'Chaise rembourrée'),
(990602, 3, 'Chaise de noble'),
(990603, 4, 'Fauteuil nain'),
(990604, 5, 'Chaise naine'),
(990605, 6, 'Chaise gnome'),
(990606, 7, 'Chaise en rondins'),
(990607, 8, 'Chaise de ferme'),
(990608, 9, 'Trône'),
(990609, 10, 'Banc en bois'),
(990610, 11, 'Banc d''auberge'),
(990611, 12, 'Banc de Hurlevent'),
(990612, 13, 'Table en bois'),
(990613, 14, 'Table d''auberge'),
(990614, 15, 'Petite table'),
(990615, 16, 'Table naine ornée'),
(990616, 17, 'Table de lecture'),
(990617, 18, 'Table gnome'),
(990618, 19, 'Lit'),
(990619, 20, 'Lits superposés'),
(990620, 21, 'Lit à baldaquin'),
(990621, 22, 'Bibliothèque'),
(990622, 23, 'Grande bibliothèque'),
(990623, 24, 'Bibliothèque garnie'),
(990624, 25, 'Étagère'),
(990625, 26, 'Armoire'),
(990626, 27, 'Armoire naine'),
(990627, 28, 'Armoire naine ornée'),
(990628, 29, 'Commode elfique'),
(990629, 30, 'Coffre'),
(990630, 31, 'Coffre ferré'),
(990631, 32, 'Coffre des Titans'),
(990632, 33, 'Tonneau'),
(990633, 34, 'Tonneau cerclé'),
(990634, 35, 'Fût de bière'),
(990635, 36, 'Caisse'),
(990636, 37, 'Caisse de grain'),
(990637, 38, 'Tonneau orc'),
(990638, 39, 'Brasero de Hurlevent'),
(990639, 40, 'Brasero magique'),
(990640, 41, 'Petit brasero'),
(990641, 42, 'Grand brasero'),
(990642, 43, 'Brasero de Lordaeron'),
(990643, 44, 'Bougie'),
(990644, 45, 'Bougie noire'),
(990645, 46, 'Lanterne elfique'),
(990646, 47, 'Poêle'),
(990647, 48, 'Tapis'),
(990648, 49, 'Tableau'),
(990649, 50, 'Tableau ancien'),
(990650, 51, 'Bannière du griffon'),
(990651, 52, 'Bannière sacrée'),
(990652, 53, 'Bannière magique'),
(990653, 54, 'Bannière de Lordaeron'),
(990654, 55, 'Bannière de clan'),
(990655, 56, 'Râtelier d''armes'),
(990656, 57, 'Bouquet de fleurs'),
(990657, 58, 'Poterie elfique'),
(990658, 59, 'Vase des Titans'),
(990659, 60, 'Statue de Khadgar'),
(990660, 61, 'Statue de lion'),
(990661, 62, 'Chaudron'),
(990662, 63, 'Table d''alchimiste');
DELETE FROM `gameobject_template` WHERE `entry` = 990590 OR `entry` BETWEEN 990600 AND 990999;
DROP TEMPORARY TABLE IF EXISTS tmp_go;
CREATE TEMPORARY TABLE tmp_go LIKE gameobject_template;
INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2713;
UPDATE tmp_go SET entry = 990590, type = 2, displayId = 26, name = 'Maison à vendre', faction = 35, flags = 0, size = 1, data0 = 0, data1 = 0, data2 = 0, data3 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990600, type = 7, displayId = 39, name = 'Chaise simple', faction = 0, flags = 0, size = 1, data0 = 1, data1 = 1;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990601, type = 7, displayId = 91, name = 'Chaise rembourrée', faction = 0, flags = 0, size = 1, data0 = 1, data1 = 1;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990602, type = 7, displayId = 92, name = 'Chaise de noble', faction = 0, flags = 0, size = 1, data0 = 1, data1 = 1;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990603, type = 7, displayId = 648, name = 'Fauteuil nain', faction = 0, flags = 0, size = 1, data0 = 1, data1 = 1;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990604, type = 7, displayId = 2088, name = 'Chaise naine', faction = 0, flags = 0, size = 1, data0 = 1, data1 = 1;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990605, type = 7, displayId = 4678, name = 'Chaise gnome', faction = 0, flags = 0, size = 1, data0 = 1, data1 = 1;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990606, type = 7, displayId = 1569, name = 'Chaise en rondins', faction = 0, flags = 0, size = 1, data0 = 1, data1 = 1;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990607, type = 7, displayId = 138, name = 'Chaise de ferme', faction = 0, flags = 0, size = 1, data0 = 1, data1 = 1;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990608, type = 7, displayId = 2810, name = 'Trône', faction = 0, flags = 0, size = 1, data0 = 1, data1 = 1;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990609, type = 7, displayId = 682, name = 'Banc en bois', faction = 0, flags = 0, size = 1, data0 = 2, data1 = 1;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990610, type = 7, displayId = 603, name = 'Banc d''auberge', faction = 0, flags = 0, size = 1, data0 = 2, data1 = 1;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990611, type = 7, displayId = 622, name = 'Banc de Hurlevent', faction = 0, flags = 0, size = 1, data0 = 2, data1 = 1;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990612, type = 5, displayId = 234, name = 'Table en bois', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990613, type = 5, displayId = 221, name = 'Table d''auberge', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990614, type = 5, displayId = 581, name = 'Petite table', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990615, type = 5, displayId = 3372, name = 'Table naine ornée', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990616, type = 5, displayId = 3371, name = 'Table de lecture', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990617, type = 5, displayId = 4091, name = 'Table gnome', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990618, type = 5, displayId = 3471, name = 'Lit', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990619, type = 5, displayId = 463, name = 'Lits superposés', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990620, type = 5, displayId = 392, name = 'Lit à baldaquin', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990621, type = 5, displayId = 188, name = 'Bibliothèque', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990622, type = 5, displayId = 187, name = 'Grande bibliothèque', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990623, type = 5, displayId = 137, name = 'Bibliothèque garnie', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990624, type = 5, displayId = 189, name = 'Étagère', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990625, type = 5, displayId = 4, name = 'Armoire', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990626, type = 5, displayId = 4031, name = 'Armoire naine', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990627, type = 5, displayId = 1227, name = 'Armoire naine ornée', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990628, type = 5, displayId = 1568, name = 'Commode elfique', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990629, type = 5, displayId = 10, name = 'Coffre', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990630, type = 5, displayId = 41, name = 'Coffre ferré', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990631, type = 5, displayId = 51, name = 'Coffre des Titans', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990632, type = 5, displayId = 32, name = 'Tonneau', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990633, type = 5, displayId = 288, name = 'Tonneau cerclé', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990634, type = 5, displayId = 1727, name = 'Fût de bière', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990635, type = 5, displayId = 31, name = 'Caisse', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990636, type = 5, displayId = 347, name = 'Caisse de grain', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990637, type = 5, displayId = 457, name = 'Tonneau orc', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990638, type = 5, displayId = 602, name = 'Brasero de Hurlevent', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990639, type = 5, displayId = 194, name = 'Brasero magique', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990640, type = 5, displayId = 201, name = 'Petit brasero', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990641, type = 5, displayId = 655, name = 'Grand brasero', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990642, type = 5, displayId = 754, name = 'Brasero de Lordaeron', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990643, type = 5, displayId = 100, name = 'Bougie', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990644, type = 5, displayId = 4152, name = 'Bougie noire', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990645, type = 5, displayId = 438, name = 'Lanterne elfique', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990646, type = 5, displayId = 348, name = 'Poêle', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990647, type = 5, displayId = 159, name = 'Tapis', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990648, type = 5, displayId = 2850, name = 'Tableau', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990649, type = 5, displayId = 4731, name = 'Tableau ancien', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990650, type = 5, displayId = 624, name = 'Bannière du griffon', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990651, type = 5, displayId = 632, name = 'Bannière sacrée', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990652, type = 5, displayId = 634, name = 'Bannière magique', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990653, type = 5, displayId = 4715, name = 'Bannière de Lordaeron', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990654, type = 5, displayId = 2552, name = 'Bannière de clan', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990655, type = 5, displayId = 130, name = 'Râtelier d''armes', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990656, type = 5, displayId = 63, name = 'Bouquet de fleurs', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990657, type = 5, displayId = 256, name = 'Poterie elfique', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990658, type = 5, displayId = 52, name = 'Vase des Titans', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990659, type = 5, displayId = 139, name = 'Statue de Khadgar', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990660, type = 5, displayId = 6, name = 'Statue de lion', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990661, type = 5, displayId = 216, name = 'Chaudron', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DELETE FROM tmp_go; INSERT INTO tmp_go SELECT * FROM gameobject_template WHERE entry = 2413;
UPDATE tmp_go SET entry = 990662, type = 5, displayId = 4391, name = 'Table d''alchimiste', faction = 0, flags = 0, size = 1, data0 = 0, data1 = 0;
INSERT INTO gameobject_template SELECT * FROM tmp_go;
DROP TEMPORARY TABLE tmp_go;
DELETE FROM `gameobject` WHERE `guid` > 9906123 AND `guid` <= 9906999;
INSERT IGNORE INTO `gameobject` (`guid`, `id`, `map`, `position_x`, `position_y`, `position_z`, `orientation`, `rotation0`, `rotation1`, `rotation2`, `rotation3`, `spawntimesecsmin`, `spawntimesecsmax`) VALUES
(9906001, 990590, 0, -8709.76, 1053.40, 97.92, 0.000, 0, 0, 0.00000, 1.00000, 25, 25),
(9906002, 990590, 0, -8540.54, 546.03, 104.70, 0.000, 0, 0, 0.00000, 1.00000, 25, 25),
(9906003, 990590, 0, -8741.36, 656.39, 107.06, 0.000, 0, 0, 0.00000, 1.00000, 25, 25),
(9906004, 990590, 0, -8826.56, 1134.01, 100.31, 0.000, 0, 0, 0.00000, 1.00000, 25, 25),
(9906005, 990590, 0, -8774.27, 1002.09, 106.91, 0.000, 0, 0, 0.00000, 1.00000, 25, 25),
(9906006, 990590, 0, -8820.39, 1089.36, 97.96, 0.000, 0, 0, 0.00000, 1.00000, 25, 25),
(9906007, 990590, 0, -8858.28, 859.60, 101.58, 0.000, 0, 0, 0.00000, 1.00000, 25, 25),
(9906008, 990590, 0, -4804.10, -1005.66, 504.45, 0.000, 0, 0, 0.00000, 1.00000, 25, 25),
(9906009, 990590, 0, -4663.46, -1162.45, 505.81, 0.000, 0, 0, 0.00000, 1.00000, 25, 25),
(9906010, 990590, 0, -4897.34, -1084.86, 504.74, 0.000, 0, 0, 0.00000, 1.00000, 25, 25),
(9906011, 990590, 0, -8823.59, 600.50, 95.58, 2.559, 0, 0, 0.95782, 0.28736, 25, 25),
(9906012, 990590, 0, -8849.25, 568.93, 94.69, 2.388, 0, 0, 0.92988, 0.36785, 25, 25),
(9906013, 990590, 0, -8892.58, 613.36, 95.26, 5.314, 0, 0, 0.46593, -0.88482, 25, 25),
(9906014, 990590, 0, -8777.42, 638.41, 97.22, 3.366, 0, 0, 0.99371, -0.11198, 25, 25),
(9906015, 990590, 0, -8795.18, 703.63, 102.28, 4.587, 0, 0, 0.74991, -0.66153, 25, 25),
(9906016, 990590, 0, -8825.20, 515.00, 98.68, 5.436, 0, 0, 0.41125, -0.91152, 25, 25),
(9906017, 990590, 0, -8711.65, 383.01, 103.73, 0.960, 0, 0, 0.46158, 0.88710, 25, 25),
(9906018, 990590, 0, -8663.33, 384.82, 104.27, 2.283, 0, 0, 0.90925, 0.41625, 25, 25),
(9906019, 990590, 0, -8656.82, 451.09, 104.25, 5.313, 0, 0, 0.46628, -0.88464, 25, 25),
(9906020, 990590, 0, -8663.09, 516.75, 101.28, 4.410, 0, 0, 0.80560, -0.59246, 25, 25),
(9906021, 990590, 0, -8659.99, 478.92, 101.20, 2.526, 0, 0, 0.95307, 0.30275, 25, 25),
(9906022, 990590, 0, -8663.64, 431.62, 100.91, 2.063, 0, 0, 0.85808, 0.51352, 25, 25),
(9906023, 990590, 0, -8466.14, 504.93, 99.78, 2.123, 0, 0, 0.87302, 0.48769, 25, 25),
(9906024, 990590, 0, -8415.21, 543.59, 95.45, 2.348, 0, 0, 0.92233, 0.38641, 25, 25),
(9906025, 990590, 0, -8391.25, 690.03, 95.27, 3.808, 0, 0, 0.94497, -0.32716, 25, 25),
(9906026, 990590, 0, -8432.69, 690.30, 96.32, 5.219, 0, 0, 0.50743, -0.86169, 25, 25),
(9906027, 990590, 0, -8551.85, 596.98, 104.60, 2.262, 0, 0, 0.90479, 0.42586, 25, 25),
(9906028, 990590, 0, -8647.60, 680.62, 101.86, 3.546, 0, 0, 0.97963, -0.20079, 25, 25),
(9906029, 990590, 0, -8696.34, 845.70, 98.69, 2.207, 0, 0, 0.89275, 0.45055, 25, 25),
(9906030, 990590, 0, -8628.72, 882.22, 103.18, 5.408, 0, 0, 0.42372, -0.90579, 25, 25),
(9906031, 990590, 0, -8672.82, 792.27, 101.72, 5.357, 0, 0, 0.44672, -0.89468, 25, 25),
(9906032, 990590, 0, -8564.08, 710.60, 103.52, 2.125, 0, 0, 0.87359, 0.48666, 25, 25),
(9906033, 990590, 0, -8549.71, 726.16, 101.72, 2.169, 0, 0, 0.88408, 0.46734, 25, 25),
(9906034, 990590, 0, -8727.04, 1173.39, 98.34, 4.328, 0, 0, 0.82912, -0.55907, 25, 25),
(9906035, 990590, 0, -8844.18, 1083.05, 95.21, 0.198, 0, 0, 0.09868, 0.99512, 25, 25),
(9906036, 990590, 0, -8856.27, 822.12, 98.32, 0.711, 0, 0, 0.34822, 0.93741, 25, 25),
(9906037, 990590, 0, -8869.65, 803.37, 97.42, 2.691, 0, 0, 0.97468, 0.22361, 25, 25),
(9906038, 990590, 0, -8940.90, 894.65, 108.10, 3.875, 0, 0, 0.93352, -0.35852, 25, 25),
(9906039, 990590, 0, -8992.98, 939.56, 117.10, 2.672, 0, 0, 0.97262, 0.23241, 25, 25),
(9906040, 990590, 0, -8887.92, 976.52, 124.36, 3.284, 0, 0, 0.99746, -0.07128, 25, 25),
(9906041, 990590, 0, -8965.05, 814.68, 109.45, 2.414, 0, 0, 0.93455, 0.35583, 25, 25),
(9906042, 990590, 0, -8887.96, 681.29, 100.08, 1.938, 0, 0, 0.82432, 0.56613, 25, 25),
(9906043, 990590, 0, -8771.05, 713.65, 99.53, 0.693, 0, 0, 0.33968, 0.94054, 25, 25),
(9906044, 990590, 0, -8869.17, 675.93, 97.90, 5.249, 0, 0, 0.49424, -0.86933, 25, 25),
(9906045, 990590, 0, -4675.69, -861.76, 503.89, 4.932, 0, 0, 0.62538, -0.78032, 25, 25),
(9906046, 990590, 0, -4652.49, -890.03, 508.86, 3.646, 0, 0, 0.96833, -0.24966, 25, 25),
(9906047, 990590, 0, -4712.99, -877.95, 501.96, 5.751, 0, 0, 0.26293, -0.96482, 25, 25),
(9906048, 990590, 0, -4713.53, -961.89, 505.29, 1.083, 0, 0, 0.51562, 0.85682, 25, 25),
(9906049, 990590, 0, -4576.64, -996.48, 504.16, 3.343, 0, 0, 0.99493, -0.10054, 25, 25),
(9906050, 990590, 0, -4595.00, -1022.13, 505.29, 1.852, 0, 0, 0.79909, 0.60122, 25, 25),
(9906051, 990590, 0, -4599.49, -1072.07, 503.59, 2.827, 0, 0, 0.98765, 0.15665, 25, 25),
(9906052, 990590, 0, -4706.76, -1176.38, 505.27, 5.585, 0, 0, 0.34226, -0.93960, 25, 25),
(9906053, 990590, 0, -4753.38, -1216.95, 501.93, 4.651, 0, 0, 0.72857, -0.68497, 25, 25),
(9906054, 990590, 0, -4967.46, -1281.93, 501.97, 0.065, 0, 0, 0.03238, 0.99948, 25, 25),
(9906055, 990590, 0, -5054.16, -1169.65, 503.68, 0.282, 0, 0, 0.14030, 0.99011, 25, 25),
(9906056, 990590, 0, -5036.81, -1142.72, 505.29, 5.061, 0, 0, 0.57357, -0.81916, 25, 25),
(9906057, 990590, 0, -4905.84, -1179.28, 503.82, 2.797, 0, 0, 0.98521, 0.17137, 25, 25),
(9906058, 990590, 0, -5029.55, -1129.54, 505.31, 0.010, 0, 0, 0.00488, 0.99999, 25, 25),
(9906059, 990590, 0, -4977.48, -1116.34, 503.69, 3.045, 0, 0, 0.99884, 0.04812, 25, 25),
(9906060, 990590, 0, -4962.38, -1035.63, 505.26, 2.680, 0, 0, 0.97350, 0.22869, 25, 25),
(9906061, 990590, 0, -5032.08, -1016.16, 508.88, 6.129, 0, 0, 0.07711, -0.99702, 25, 25),
(9906062, 990590, 0, -5024.42, -995.42, 503.88, 0.002, 0, 0, 0.00094, 1.00000, 25, 25),
(9906063, 990590, 0, -4922.55, -1004.80, 502.00, 0.556, 0, 0, 0.27422, 0.96167, 25, 25),
(9906064, 990590, 0, -4876.83, -972.68, 505.07, 1.998, 0, 0, 0.84102, 0.54100, 25, 25),
(9906065, 990590, 0, -4831.46, -922.71, 502.22, 1.953, 0, 0, 0.82848, 0.56002, 25, 25),
(9906066, 990590, 0, -4771.38, -925.65, 503.69, 1.120, 0, 0, 0.53130, 0.84718, 25, 25),
(9906067, 990590, 0, -4693.78, -1005.00, 502.21, 4.826, 0, 0, 0.66590, -0.74604, 25, 25),
(9906068, 990590, 0, -4737.69, -1010.38, 503.66, 4.370, 0, 0, 0.81717, -0.57640, 25, 25),
(9906069, 990590, 0, -4710.98, -1080.84, 502.77, 3.274, 0, 0, 0.99782, -0.06606, 25, 25),
(9906070, 990590, 0, -4704.53, -1114.33, 504.44, 2.744, 0, 0, 0.98035, 0.19727, 25, 25),
(9906071, 990590, 0, -4722.31, -1152.28, 502.45, 2.696, 0, 0, 0.97526, 0.22108, 25, 25),
(9906072, 990590, 0, -4772.23, -1188.43, 502.73, 0.316, 0, 0, 0.15731, 0.98755, 25, 25),
(9906073, 990590, 0, -4835.97, -1181.60, 502.47, 6.125, 0, 0, 0.07915, -0.99686, 25, 25),
(9906074, 990590, 0, -4857.60, -1173.23, 504.18, 4.004, 0, 0, 0.90843, -0.41803, 25, 25),
(9906075, 990590, 1, -1249.15, 152.78, 133.55, 4.940, 0, 0, 0.62208, -0.78295, 25, 25),
(9906076, 990590, 1, -1243.43, 42.87, 127.09, 0.537, 0, 0, 0.26550, 0.96411, 25, 25),
(9906077, 990590, 1, -1289.42, 75.72, 128.67, 4.173, 0, 0, 0.86994, -0.49316, 25, 25),
(9906078, 990590, 1, -1265.38, 142.02, 132.59, 1.720, 0, 0, 0.75792, 0.65235, 25, 25),
(9906079, 990590, 1, -1375.06, -100.22, 158.94, 2.945, 0, 0, 0.99516, 0.09831, 25, 25),
(9906080, 990590, 1, 9667.84, 2379.49, 1337.31, 2.726, 0, 0, 0.97849, 0.20630, 25, 25),
(9906081, 990590, 1, 9699.11, 2226.17, 1330.01, 0.978, 0, 0, 0.46962, 0.88287, 25, 25),
(9906082, 990590, 1, 9845.05, 2183.47, 1329.98, 5.011, 0, 0, 0.59416, -0.80435, 25, 25),
(9906083, 990590, 1, 9886.79, 2320.86, 1327.96, 0.707, 0, 0, 0.34607, 0.93821, 25, 25),
(9906084, 990590, 1, 10138.30, 2215.34, 1329.98, 5.337, 0, 0, 0.45578, -0.89009, 25, 25),
(9906085, 990590, 1, 10217.30, 2337.25, 1330.00, 6.272, 0, 0, 0.00554, -0.99998, 25, 25),
(9906086, 990590, 1, 1588.34, -4470.34, 7.67, 4.652, 0, 0, 0.72818, -0.68539, 25, 25),
(9906087, 990590, 1, 1691.14, -4410.77, 21.68, 3.721, 0, 0, 0.95830, -0.28575, 25, 25),
(9906088, 990590, 1, 1742.91, -4317.99, 33.37, 3.779, 0, 0, 0.94972, -0.31311, 25, 25),
(9906089, 990590, 1, 1576.22, -4291.77, 25.92, 1.035, 0, 0, 0.49476, 0.86903, 25, 25),
(9906090, 990590, 1, 1518.14, -4354.92, 18.66, 3.146, 0, 0, 1.00000, -0.00195, 25, 25),
(9906091, 990590, 1, 1839.44, -4469.49, 47.45, 1.441, 0, 0, 0.65968, 0.75155, 25, 25),
(9906092, 990590, 1, 1902.71, -4456.58, 53.20, 5.438, 0, 0, 0.40992, -0.91212, 25, 25),
(9906093, 990590, 1, 1929.32, -4514.83, 29.06, 4.592, 0, 0, 0.74844, -0.66320, 25, 25),
(9906094, 990590, 1, 1802.62, -4567.00, 22.78, 1.389, 0, 0, 0.63996, 0.76841, 25, 25),
(9906095, 990590, 1, 1880.12, -4706.55, 39.28, 4.184, 0, 0, 0.86720, -0.49797, 25, 25),
(9906096, 990590, 1, 1908.86, -4783.06, 36.18, 1.285, 0, 0, 0.59928, 0.80054, 25, 25),
(9906097, 990590, 1, 2026.97, -4704.65, 26.80, 5.639, 0, 0, 0.31671, -0.94852, 25, 25),
(9906098, 990590, 1, 2052.65, -4837.49, 24.35, 4.150, 0, 0, 0.87567, -0.48292, 25, 25),
(9906099, 990590, 1, 2028.79, -4636.79, 29.55, 1.039, 0, 0, 0.49662, 0.86797, 25, 25),
(9906100, 990590, 1, 1891.98, -4321.71, 23.17, 5.913, 0, 0, 0.18413, -0.98290, 25, 25),
(9906101, 990590, 1, 1783.89, -4205.54, 40.01, 4.430, 0, 0, 0.79961, -0.60053, 25, 25),
(9906102, 990590, 1, 1748.24, -4323.04, 5.91, 3.879, 0, 0, 0.93287, -0.36020, 25, 25),
(9906103, 990590, 1, 1810.69, -4276.08, 7.11, 0.687, 0, 0, 0.33702, 0.94150, 25, 25),
(9906104, 990590, 1, 1773.57, -4282.12, 7.73, 2.173, 0, 0, 0.88493, 0.46573, 25, 25),
(9906105, 990590, 1, 1828.06, -4298.16, -12.40, 3.094, 0, 0, 0.99972, 0.02383, 25, 25),
(9906106, 990590, 1, 1840.92, -4321.86, -15.70, 0.830, 0, 0, 0.40337, 0.91504, 25, 25),
(9906107, 990590, 1, 1805.41, -4371.72, -17.48, 1.367, 0, 0, 0.63142, 0.77544, 25, 25),
(9906108, 990590, 1, 1766.73, -4367.56, -16.02, 1.990, 0, 0, 0.83886, 0.54434, 25, 25),
(9906109, 990590, 1, 1579.46, -4096.71, 36.24, 5.080, 0, 0, 0.56590, -0.82447, 25, 25),
(9906110, 990590, 1, 1781.53, -3994.25, 53.16, 0.044, 0, 0, 0.02207, 0.99976, 25, 25),
(9906111, 990590, 0, 1633.90, 202.02, -43.10, 2.287, 0, 0, 0.91014, 0.41430, 25, 25),
(9906112, 990590, 0, 1572.20, 190.16, -43.10, 4.277, 0, 0, 0.84302, -0.53789, 25, 25),
(9906113, 990590, 0, 1557.85, 203.92, -43.10, 0.432, 0, 0, 0.21439, 0.97675, 25, 25),
(9906114, 990590, 0, 1546.29, 260.39, -43.10, 3.220, 0, 0, 0.99923, -0.03935, 25, 25),
(9906115, 990590, 0, 1645.13, 261.49, -43.10, 3.502, 0, 0, 0.98378, -0.17936, 25, 25),
(9906116, 990590, 0, 1631.46, 277.55, -43.10, 0.579, 0, 0, 0.28545, 0.95839, 25, 25),
(9906117, 990590, 0, -9377.76, -72.06, 64.44, 1.173, 0, 0, 0.55344, 0.83289, 25, 25),
(9906118, 990590, 0, 2261.50, 344.54, 36.02, 5.959, 0, 0, 0.16140, -0.98689, 25, 25),
(9906119, 990590, 0, -5504.13, -703.04, 393.16, 1.115, 0, 0, 0.52897, 0.84864, 25, 25),
(9906120, 990590, 0, -5533.85, -667.86, 393.33, 0.673, 0, 0, 0.32999, 0.94398, 25, 25),
(9906121, 990590, 1, 9774.26, 879.48, 1297.70, 1.365, 0, 0, 0.63072, 0.77601, 25, 25),
(9906122, 990590, 1, -2184.78, -414.83, -4.50, 3.972, 0, 0, 0.91512, -0.40318, 25, 25),
(9906123, 990590, 1, -2344.15, -310.87, -9.38, 2.558, 0, 0, 0.95771, 0.28774, 25, 25);
CREATE TABLE IF NOT EXISTS `custom_maison_deco_retiree` LIKE `gameobject`;
INSERT IGNORE INTO `custom_maison_deco_retiree` SELECT g.* FROM gameobject g JOIN gameobject_template t ON t.entry = g.id WHERE (t.type = 7 OR (t.type = 5 AND t.displayId IN (4,5,9,18,30,31,32,33,39,52,53,63,91,92,100,112,113,137,138,151,159,187,188,189,216,221,234,253,256,257,275,279,285,286,287,288,319,331,347,348,380,383,436,457,463,521,581,603,622,623,648,651,679,682,987,988,989,990,1227,1568,1569,1727,1868,1869,1988,2087,2088,2350,3231,3232,3371,3372,3471,3791,4031,4091,4152,4331,4352,4391,4678))) AND g.guid < 9900000 AND g.guid NOT IN (SELECT guid FROM game_event_gameobject) AND ((g.map = 0 AND g.position_x BETWEEN -8729.76 AND -8689.76 AND g.position_y BETWEEN 1033.40 AND 1073.40 AND g.position_z BETWEEN 95.92 AND 107.75) OR (g.map = 0 AND g.position_x BETWEEN -8557.10 AND -8523.97 AND g.position_y BETWEEN 533.41 AND 566.03 AND g.position_z BETWEEN 102.70 AND 109.85) OR (g.map = 0 AND g.position_x BETWEEN -8760.50 AND -8729.96 AND g.position_y BETWEEN 641.27 AND 671.50 AND g.position_z BETWEEN 105.06 AND 112.21) OR (g.map = 0 AND g.position_x BETWEEN -8841.33 AND -8811.79 AND g.position_y BETWEEN 1119.20 AND 1148.82 AND g.position_z BETWEEN 98.31 AND 105.46) OR (g.map = 0 AND g.position_x BETWEEN -8788.50 AND -8760.04 AND g.position_y BETWEEN 987.81 AND 1016.36 AND g.position_z BETWEEN 104.91 AND 112.06) OR (g.map = 0 AND g.position_x BETWEEN -8830.23 AND -8808.07 AND g.position_y BETWEEN 1078.88 AND 1102.21 AND g.position_z BETWEEN 95.96 AND 101.96) OR (g.map = 0 AND g.position_x BETWEEN -8869.47 AND -8847.08 AND g.position_y BETWEEN 848.23 AND 870.96 AND g.position_z BETWEEN 99.58 AND 106.73) OR (g.map = 0 AND g.position_x BETWEEN -4822.21 AND -4785.99 AND g.position_y BETWEEN -1023.51 AND -987.80 AND g.position_z BETWEEN 502.45 AND 517.06) OR (g.map = 0 AND g.position_x BETWEEN -4681.25 AND -4645.67 AND g.position_y BETWEEN -1180.07 AND -1144.84 AND g.position_z BETWEEN 503.81 AND 517.73) OR (g.map = 0 AND g.position_x BETWEEN -4914.32 AND -4880.36 AND g.position_y BETWEEN -1101.48 AND -1068.24 AND g.position_z BETWEEN 502.74 AND 515.32) OR (g.map = 0 AND g.position_x BETWEEN -8838.94 AND -8811.86 AND g.position_y BETWEEN 584.94 AND 612.17 AND g.position_z BETWEEN 95.51 AND 102.69) OR (g.map = 0 AND g.position_x BETWEEN -8865.60 AND -8841.02 AND g.position_y BETWEEN 556.34 AND 581.30 AND g.position_z BETWEEN 94.64 AND 108.27) OR (g.map = 0 AND g.position_x BETWEEN -8900.57 AND -8877.08 AND g.position_y BETWEEN 599.23 AND 625.19 AND g.position_z BETWEEN 95.21 AND 102.37) OR (g.map = 0 AND g.position_x BETWEEN -8789.79 AND -8761.74 AND g.position_y BETWEEN 626.85 AND 654.87 AND g.position_z BETWEEN 97.11 AND 105.72) OR (g.map = 0 AND g.position_x BETWEEN -8808.21 AND -8777.53 AND g.position_y BETWEEN 685.90 AND 716.62 AND g.position_z BETWEEN 102.23 AND 115.87) OR (g.map = 0 AND g.position_x BETWEEN -8832.29 AND -8809.36 AND g.position_y BETWEEN 504.44 AND 527.89 AND g.position_z BETWEEN 98.65 AND 112.26) OR (g.map = 0 AND g.position_x BETWEEN -8722.91 AND -8695.29 AND g.position_y BETWEEN 368.06 AND 395.63 AND g.position_z BETWEEN 103.61 AND 112.22) OR (g.map = 0 AND g.position_x BETWEEN -8674.00 AND -8651.07 AND g.position_y BETWEEN 377.38 AND 400.83 AND g.position_z BETWEEN 104.24 AND 117.85) OR (g.map = 0 AND g.position_x BETWEEN -8665.80 AND -8642.87 AND g.position_y BETWEEN 438.78 AND 462.23 AND g.position_z BETWEEN 104.18 AND 117.83) OR (g.map = 0 AND g.position_x BETWEEN -8676.87 AND -8646.19 AND g.position_y BETWEEN 497.49 AND 528.10 AND g.position_z BETWEEN 101.24 AND 114.86) OR (g.map = 0 AND g.position_x BETWEEN -8674.57 AND -8652.18 AND g.position_y BETWEEN 466.68 AND 489.41 AND g.position_z BETWEEN 101.09 AND 108.32) OR (g.map = 0 AND g.position_x BETWEEN -8676.99 AND -8654.51 AND g.position_y BETWEEN 419.48 AND 442.32 AND g.position_z BETWEEN 100.87 AND 108.02) OR (g.map = 0 AND g.position_x BETWEEN -8473.14 AND -8459.14 AND g.position_y BETWEEN 497.93 AND 511.93 AND g.position_z BETWEEN 97.78 AND 107.78) OR (g.map = 0 AND g.position_x BETWEEN -8428.25 AND -8404.00 AND g.position_y BETWEEN 535.26 AND 560.33 AND g.position_z BETWEEN 95.41 AND 102.56) OR (g.map = 0 AND g.position_x BETWEEN -8402.66 AND -8379.21 AND g.position_y BETWEEN 673.22 AND 696.16 AND g.position_z BETWEEN 95.24 AND 108.86) OR (g.map = 0 AND g.position_x BETWEEN -8440.40 AND -8416.14 AND g.position_y BETWEEN 675.76 AND 700.83 AND g.position_z BETWEEN 96.28 AND 103.43) OR (g.map = 0 AND g.position_x BETWEEN -8569.06 AND -8545.98 AND g.position_y BETWEEN 585.08 AND 608.68 AND g.position_z BETWEEN 104.55 AND 118.18) OR (g.map = 0 AND g.position_x BETWEEN -8659.92 AND -8636.33 AND g.position_y BETWEEN 664.67 AND 687.75 AND g.position_z BETWEEN 101.72 AND 115.34) OR (g.map = 0 AND g.position_x BETWEEN -8710.89 AND -8687.95 AND g.position_y BETWEEN 832.46 AND 855.91 AND g.position_z BETWEEN 98.66 AND 112.27) OR (g.map = 0 AND g.position_x BETWEEN -8637.76 AND -8614.92 AND g.position_y BETWEEN 871.11 AND 894.40 AND g.position_z BETWEEN 103.12 AND 110.30) OR (g.map = 0 AND g.position_x BETWEEN -8680.84 AND -8658.45 AND g.position_y BETWEEN 781.74 AND 804.46 AND g.position_z BETWEEN 101.60 AND 108.83) OR (g.map = 0 AND g.position_x BETWEEN -8577.98 AND -8555.13 AND g.position_y BETWEEN 697.37 AND 720.66 AND g.position_z BETWEEN 103.46 AND 110.64) OR (g.map = 0 AND g.position_x BETWEEN -8566.80 AND -8542.54 AND g.position_y BETWEEN 714.24 AND 739.30 AND g.position_z BETWEEN 101.68 AND 108.83) OR (g.map = 0 AND g.position_x BETWEEN -8734.04 AND -8720.04 AND g.position_y BETWEEN 1166.39 AND 1180.39 AND g.position_z BETWEEN 96.34 AND 106.34) OR (g.map = 0 AND g.position_x BETWEEN -8851.18 AND -8837.18 AND g.position_y BETWEEN 1076.05 AND 1090.05 AND g.position_z BETWEEN 93.21 AND 103.21) OR (g.map = 0 AND g.position_x BETWEEN -8871.37 AND -8844.73 AND g.position_y BETWEEN 813.19 AND 838.66 AND g.position_z BETWEEN 98.29 AND 111.90) OR (g.map = 0 AND g.position_x BETWEEN -8885.71 AND -8855.73 AND g.position_y BETWEEN 786.39 AND 816.44 AND g.position_z BETWEEN 97.36 AND 111.00) OR (g.map = 0 AND g.position_x BETWEEN -8957.46 AND -8932.04 AND g.position_y BETWEEN 883.53 AND 908.73 AND g.position_z BETWEEN 108.07 AND 115.22) OR (g.map = 0 AND g.position_x BETWEEN -9007.43 AND -8978.13 AND g.position_y BETWEEN 927.01 AND 956.39 AND g.position_z BETWEEN 117.05 AND 124.21) OR (g.map = 0 AND g.position_x BETWEEN -8900.68 AND -8870.23 AND g.position_y BETWEEN 965.14 AND 995.55 AND g.position_z BETWEEN 124.32 AND 131.47) OR (g.map = 0 AND g.position_x BETWEEN -8976.66 AND -8953.64 AND g.position_y BETWEEN 804.41 AND 827.73 AND g.position_z BETWEEN 109.41 AND 116.56) OR (g.map = 0 AND g.position_x BETWEEN -8900.27 AND -8877.06 AND g.position_y BETWEEN 669.37 AND 692.78 AND g.position_z BETWEEN 100.02 AND 107.20) OR (g.map = 0 AND g.position_x BETWEEN -8783.19 AND -8758.70 AND g.position_y BETWEEN 705.40 AND 729.35 AND g.position_z BETWEEN 99.50 AND 113.12) OR (g.map = 0 AND g.position_x BETWEEN -8877.51 AND -8852.16 AND g.position_y BETWEEN 662.64 AND 688.64 AND g.position_z BETWEEN 97.87 AND 105.02) OR (g.map = 0 AND g.position_x BETWEEN -4694.89 AND -4659.53 AND g.position_y BETWEEN -881.76 AND -849.21 AND g.position_z BETWEEN 503.86 AND 517.78) OR (g.map = 0 AND g.position_x BETWEEN -4670.18 AND -4644.17 AND g.position_y BETWEEN -904.60 AND -877.81 AND g.position_z BETWEEN 504.86 AND 514.89) OR (g.map = 0 AND g.position_x BETWEEN -4729.78 AND -4694.80 AND g.position_y BETWEEN -892.74 AND -858.39 AND g.position_z BETWEEN 501.93 AND 514.49) OR (g.map = 0 AND g.position_x BETWEEN -4729.56 AND -4701.64 AND g.position_y BETWEEN -971.32 AND -944.11 AND g.position_z BETWEEN 505.26 AND 517.88) OR (g.map = 0 AND g.position_x BETWEEN -4591.19 AND -4565.74 AND g.position_y BETWEEN -1007.13 AND -982.02 AND g.position_z BETWEEN 503.63 AND 516.50) OR (g.map = 0 AND g.position_x BETWEEN -4613.72 AND -4583.77 AND g.position_y BETWEEN -1036.86 AND -1006.62 AND g.position_z BETWEEN 505.26 AND 517.88) OR (g.map = 0 AND g.position_x BETWEEN -4619.49 AND -4585.94 AND g.position_y BETWEEN -1092.07 AND -1056.66 AND g.position_z BETWEEN 503.56 AND 517.48) OR (g.map = 0 AND g.position_x BETWEEN -4726.76 AND -4687.25 AND g.position_y BETWEEN -1196.38 AND -1156.38 AND g.position_z BETWEEN 501.67 AND 520.27) OR (g.map = 0 AND g.position_x BETWEEN -4768.10 AND -4737.55 AND g.position_y BETWEEN -1229.84 AND -1199.82 AND g.position_z BETWEEN 501.90 AND 516.51) OR (g.map = 0 AND g.position_x BETWEEN -4985.03 AND -4950.43 AND g.position_y BETWEEN -1300.99 AND -1266.49 AND g.position_z BETWEEN 501.92 AND 516.55) OR (g.map = 0 AND g.position_x BETWEEN -5066.99 AND -5041.54 AND g.position_y BETWEEN -1183.04 AND -1157.93 AND g.position_z BETWEEN 503.65 AND 516.52) OR (g.map = 0 AND g.position_x BETWEEN -5048.96 AND -5016.81 AND g.position_y BETWEEN -1158.44 AND -1122.72 AND g.position_z BETWEEN 505.26 AND 517.90) OR (g.map = 0 AND g.position_x BETWEEN -4925.84 AND -4890.03 AND g.position_y BETWEEN -1193.08 AND -1159.28 AND g.position_z BETWEEN 503.79 AND 517.71) OR (g.map = 0 AND g.position_x BETWEEN -5048.96 AND -5012.99 AND g.position_y BETWEEN -1149.54 AND -1111.80 AND g.position_z BETWEEN 505.26 AND 517.90) OR (g.map = 0 AND g.position_x BETWEEN -4988.88 AND -4962.83 AND g.position_y BETWEEN -1126.81 AND -1101.06 AND g.position_z BETWEEN 503.66 AND 516.52) OR (g.map = 0 AND g.position_x BETWEEN -4979.41 AND -4944.10 AND g.position_y BETWEEN -1052.71 AND -1015.63 AND g.position_z BETWEEN 503.84 AND 517.85) OR (g.map = 0 AND g.position_x BETWEEN -5044.03 AND -5012.37 AND g.position_y BETWEEN -1031.49 AND -1000.18 AND g.position_z BETWEEN 504.88 AND 514.90) OR (g.map = 0 AND g.position_x BETWEEN -5034.72 AND -5004.42 AND g.position_y BETWEEN -1014.73 AND -978.02 AND g.position_z BETWEEN 503.85 AND 517.77) OR (g.map = 0 AND g.position_x BETWEEN -4931.37 AND -4904.46 AND g.position_y BETWEEN -1016.86 AND -990.64 AND g.position_z BETWEEN 501.97 AND 513.20) OR (g.map = 0 AND g.position_x BETWEEN -4896.83 AND -4860.91 AND g.position_y BETWEEN -992.68 AND -955.38 AND g.position_z BETWEEN 503.91 AND 519.47) OR (g.map = 0 AND g.position_x BETWEEN -4847.27 AND -4815.60 AND g.position_y BETWEEN -941.84 AND -908.84 AND g.position_z BETWEEN 502.19 AND 514.76) OR (g.map = 0 AND g.position_x BETWEEN -4782.88 AND -4755.92 AND g.position_y BETWEEN -940.38 AND -913.32 AND g.position_z BETWEEN 503.66 AND 516.52) OR (g.map = 0 AND g.position_x BETWEEN -4701.63 AND -4673.78 AND g.position_y BETWEEN -1020.19 AND -992.54 AND g.position_z BETWEEN 502.18 AND 514.90) OR (g.map = 0 AND g.position_x BETWEEN -4749.97 AND -4722.78 AND g.position_y BETWEEN -1023.47 AND -996.09 AND g.position_z BETWEEN 503.63 AND 516.50) OR (g.map = 0 AND g.position_x BETWEEN -4721.83 AND -4699.99 AND g.position_y BETWEEN -1091.67 AND -1069.87 AND g.position_z BETWEEN 502.74 AND 509.03) OR (g.map = 0 AND g.position_x BETWEEN -4724.53 AND -4689.98 AND g.position_y BETWEEN -1134.33 AND -1094.62 AND g.position_z BETWEEN 504.41 AND 518.34) OR (g.map = 0 AND g.position_x BETWEEN -4731.67 AND -4710.14 AND g.position_y BETWEEN -1163.34 AND -1141.74 AND g.position_z BETWEEN 502.42 AND 508.71) OR (g.map = 0 AND g.position_x BETWEEN -4779.80 AND -4752.23 AND g.position_y BETWEEN -1202.59 AND -1175.51 AND g.position_z BETWEEN 502.70 AND 515.42) OR (g.map = 0 AND g.position_x BETWEEN -4851.17 AND -4815.97 AND g.position_y BETWEEN -1201.60 AND -1169.45 AND g.position_z BETWEEN 502.44 AND 515.00) OR (g.map = 0 AND g.position_x BETWEEN -4868.94 AND -4845.83 AND g.position_y BETWEEN -1185.83 AND -1162.92 AND g.position_z BETWEEN 504.15 AND 517.02) OR (g.map = 1 AND g.position_x BETWEEN -1264.04 AND -1232.63 AND g.position_y BETWEEN 137.49 AND 170.43 AND g.position_z BETWEEN 132.51 AND 148.55) OR (g.map = 1 AND g.position_x BETWEEN -1263.43 AND -1242.45 AND g.position_y BETWEEN 22.87 AND 42.04 AND g.position_z BETWEEN 127.15 AND 142.09) OR (g.map = 1 AND g.position_x BETWEEN -1296.42 AND -1282.42 AND g.position_y BETWEEN 68.72 AND 82.72 AND g.position_z BETWEEN 126.67 AND 136.67) OR (g.map = 1 AND g.position_x BETWEEN -1272.38 AND -1258.38 AND g.position_y BETWEEN 135.02 AND 149.02 AND g.position_z BETWEEN 130.59 AND 140.59) OR (g.map = 1 AND g.position_x BETWEEN -1382.06 AND -1368.06 AND g.position_y BETWEEN -107.22 AND -93.22 AND g.position_z BETWEEN 156.94 AND 166.94) OR (g.map = 1 AND g.position_x BETWEEN 9660.84 AND 9674.84 AND g.position_y BETWEEN 2372.49 AND 2386.49 AND g.position_z BETWEEN 1335.31 AND 1345.31) OR (g.map = 1 AND g.position_x BETWEEN 9687.38 AND 9712.32 AND g.position_y BETWEEN 2212.79 AND 2238.18 AND g.position_z BETWEEN 1329.94 AND 1336.32) OR (g.map = 1 AND g.position_x BETWEEN 9834.84 AND 9853.97 AND g.position_y BETWEEN 2174.74 AND 2194.65 AND g.position_z BETWEEN 1329.93 AND 1336.32) OR (g.map = 1 AND g.position_x BETWEEN 9879.79 AND 9893.79 AND g.position_y BETWEEN 2313.86 AND 2327.86 AND g.position_z BETWEEN 1325.96 AND 1335.96) OR (g.map = 1 AND g.position_x BETWEEN 10125.59 AND 10150.35 AND g.position_y BETWEEN 2204.15 AND 2229.05 AND g.position_z BETWEEN 1329.94 AND 1336.32) OR (g.map = 1 AND g.position_x BETWEEN 10205.33 AND 10225.80 AND g.position_y BETWEEN 2328.53 AND 2348.23 AND g.position_z BETWEEN 1329.94 AND 1336.32) OR (g.map = 1 AND g.position_x BETWEEN 1572.99 AND 1608.34 AND g.position_y BETWEEN -4490.34 AND -4450.34 AND g.position_z BETWEEN 6.73 AND 14.93) OR (g.map = 1 AND g.position_x BETWEEN 1675.45 AND 1711.14 AND g.position_y BETWEEN -4430.77 AND -4395.00 AND g.position_z BETWEEN 21.53 AND 28.82) OR (g.map = 1 AND g.position_x BETWEEN 1725.46 AND 1762.91 AND g.position_y BETWEEN -4335.30 AND -4297.99 AND g.position_z BETWEEN 33.02 AND 44.87) OR (g.map = 1 AND g.position_x BETWEEN 1556.42 AND 1592.70 AND g.position_y BETWEEN -4309.09 AND -4272.94 AND g.position_z BETWEEN 25.66 AND 37.52) OR (g.map = 1 AND g.position_x BETWEEN 1500.67 AND 1536.49 AND g.position_y BETWEEN -4372.73 AND -4336.55 AND g.position_z BETWEEN 18.44 AND 30.30) OR (g.map = 1 AND g.position_x BETWEEN 1819.44 AND 1855.98 AND g.position_y BETWEEN -4488.24 AND -4449.49 AND g.position_z BETWEEN 47.33 AND 54.62) OR (g.map = 1 AND g.position_x BETWEEN 1890.31 AND 1918.02 AND g.position_y BETWEEN -4471.00 AND -4442.77 AND g.position_z BETWEEN 53.17 AND 61.20) OR (g.map = 1 AND g.position_x BETWEEN 1916.95 AND 1944.84 AND g.position_y BETWEEN -4531.26 AND -4502.96 AND g.position_z BETWEEN 29.03 AND 37.07) OR (g.map = 1 AND g.position_x BETWEEN 1782.62 AND 1822.62 AND g.position_y BETWEEN -4587.00 AND -4547.00 AND g.position_z BETWEEN 22.75 AND 34.27) OR (g.map = 1 AND g.position_x BETWEEN 1860.12 AND 1898.71 AND g.position_y BETWEEN -4726.55 AND -4690.03 AND g.position_z BETWEEN 39.19 AND 46.48) OR (g.map = 1 AND g.position_x BETWEEN 1891.54 AND 1928.86 AND g.position_y BETWEEN -4800.90 AND -4763.06 AND g.position_z BETWEEN 35.29 AND 43.49) OR (g.map = 1 AND g.position_x BETWEEN 2013.74 AND 2041.80 AND g.position_y BETWEEN -4719.14 AND -4691.21 AND g.position_z BETWEEN 26.78 AND 34.81) OR (g.map = 1 AND g.position_x BETWEEN 2045.65 AND 2059.65 AND g.position_y BETWEEN -4844.49 AND -4830.49 AND g.position_z BETWEEN 22.35 AND 32.35) OR (g.map = 1 AND g.position_x BETWEEN 2008.79 AND 2045.48 AND g.position_y BETWEEN -4654.68 AND -4617.84 AND g.position_z BETWEEN 29.53 AND 42.73) OR (g.map = 1 AND g.position_x BETWEEN 1871.98 AND 1908.85 AND g.position_y BETWEEN -4341.71 AND -4303.80 AND g.position_z BETWEEN 22.72 AND 31.19) OR (g.map = 1 AND g.position_x BETWEEN 1765.23 AND 1802.83 AND g.position_y BETWEEN -4223.90 AND -4186.63 AND g.position_z BETWEEN 39.98 AND 53.18) OR (g.map = 1 AND g.position_x BETWEEN 1741.24 AND 1755.24 AND g.position_y BETWEEN -4330.04 AND -4316.04 AND g.position_z BETWEEN 3.91 AND 13.91) OR (g.map = 1 AND g.position_x BETWEEN 1803.69 AND 1817.69 AND g.position_y BETWEEN -4283.08 AND -4269.08 AND g.position_z BETWEEN 5.11 AND 15.11) OR (g.map = 1 AND g.position_x BETWEEN 1766.57 AND 1780.57 AND g.position_y BETWEEN -4289.12 AND -4275.12 AND g.position_z BETWEEN 5.73 AND 15.73) OR (g.map = 1 AND g.position_x BETWEEN 1821.06 AND 1835.06 AND g.position_y BETWEEN -4305.16 AND -4291.16 AND g.position_z BETWEEN -14.40 AND -4.40) OR (g.map = 1 AND g.position_x BETWEEN 1833.92 AND 1847.92 AND g.position_y BETWEEN -4328.86 AND -4314.86 AND g.position_z BETWEEN -17.70 AND -7.70) OR (g.map = 1 AND g.position_x BETWEEN 1798.41 AND 1812.41 AND g.position_y BETWEEN -4378.72 AND -4364.72 AND g.position_z BETWEEN -19.48 AND -9.48) OR (g.map = 1 AND g.position_x BETWEEN 1759.73 AND 1773.73 AND g.position_y BETWEEN -4374.56 AND -4360.56 AND g.position_z BETWEEN -18.02 AND -8.02) OR (g.map = 1 AND g.position_x BETWEEN 1559.46 AND 1597.70 AND g.position_y BETWEEN -4114.80 AND -4076.80 AND g.position_z BETWEEN 35.90 AND 46.77) OR (g.map = 1 AND g.position_x BETWEEN 1768.02 AND 1795.69 AND g.position_y BETWEEN -4007.61 AND -3979.88 AND g.position_z BETWEEN 53.14 AND 61.17) OR (g.map = 0 AND g.position_x BETWEEN 1619.71 AND 1640.47 AND g.position_y BETWEEN 193.86 AND 214.97 AND g.position_z BETWEEN -43.15 AND -28.10) OR (g.map = 0 AND g.position_x BETWEEN 1566.70 AND 1585.67 AND g.position_y BETWEEN 182.34 AND 204.47 AND g.position_z BETWEEN -43.13 AND -28.96) OR (g.map = 0 AND g.position_x BETWEEN 1550.31 AND 1571.07 AND g.position_y BETWEEN 194.47 AND 215.58 AND g.position_z BETWEEN -43.14 AND -28.10) OR (g.map = 0 AND g.position_x BETWEEN 1538.08 AND 1560.38 AND g.position_y BETWEEN 251.35 AND 270.58 AND g.position_z BETWEEN -43.14 AND -28.93) OR (g.map = 0 AND g.position_x BETWEEN 1631.38 AND 1653.68 AND g.position_y BETWEEN 250.53 AND 269.77 AND g.position_z BETWEEN -43.13 AND -28.93) OR (g.map = 0 AND g.position_x BETWEEN 1620.33 AND 1641.09 AND g.position_y BETWEEN 265.07 AND 286.18 AND g.position_z BETWEEN -43.13 AND -28.10) OR (g.map = 0 AND g.position_x BETWEEN -9386.08 AND -9365.35 AND g.position_y BETWEEN -83.00 AND -56.51 AND g.position_z BETWEEN 64.37 AND 68.89) OR (g.map = 0 AND g.position_x BETWEEN 2251.70 AND 2270.33 AND g.position_y BETWEEN 336.70 AND 354.88 AND g.position_z BETWEEN 35.96 AND 45.18) OR (g.map = 0 AND g.position_x BETWEEN -5515.10 AND -5489.34 AND g.position_y BETWEEN -714.67 AND -686.87 AND g.position_z BETWEEN 391.72 AND 399.47) OR (g.map = 0 AND g.position_x BETWEEN -5542.21 AND -5513.85 AND g.position_y BETWEEN -678.02 AND -651.29 AND g.position_z BETWEEN 392.40 AND 405.58) OR (g.map = 1 AND g.position_x BETWEEN 9761.17 AND 9781.61 AND g.position_y BETWEEN 870.06 AND 884.88 AND g.position_z BETWEEN 1297.27 AND 1306.40) OR (g.map = 1 AND g.position_x BETWEEN -2191.78 AND -2177.78 AND g.position_y BETWEEN -421.83 AND -407.83 AND g.position_z BETWEEN -6.50 AND 3.50) OR (g.map = 1 AND g.position_x BETWEEN -2351.15 AND -2337.15 AND g.position_y BETWEEN -317.87 AND -303.87 AND g.position_z BETWEEN -11.38 AND -1.38));
DELETE FROM `gameobject` WHERE `guid` IN (SELECT `guid` FROM `custom_maison_deco_retiree`);
SELECT 'Logement OK' AS resultat;
