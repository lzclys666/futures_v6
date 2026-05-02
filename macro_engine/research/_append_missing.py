)
        self.assertGreater(curve.iloc[0], 0.05, "初始IC应较高")
        self.assertFalse(curve.isna().all())

    def test_half_life(self):
        """测试: 半衰期计算"""
        decay = FactorDecayAnalyzer(max_lag=20)
        curve = pd.Series({1: 0.10, 2: 0.08, 3: 0.06, 4: 0.04, 5: 0.02})
        hl = decay.compute_half_life(curve)
        self.assertIsNotNone(hl)


# ============================================================
# 主程序：运行测试 + 示例演示
# ============================================================

if __name__ == "__main__":
    import sys
    print("=" * 80)
    print("Phase 2 Statistical Modules - hmmlearn + PIT 版本")
    print("=" * 80)

    # 运行单元测试
    print("\n[单元测试]")
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    passed = result.testsRun - len(result.failures) - len(result.errors)
    print(f"\n测试结果: {passed}/{result.testsRun} 通过")

    if result.failures or result.errors:
        print("\n失败详情:")
        for tb in result.failures + result.errors:
            print(tb[0])

    # 示例演示
    if not result.failures and not result.errors:
        print("\n" + "=" * 80)
        print("示例演示")
        print("=" * 80)

        base_path = r"D:\futures_v6\macro_engine\data\crawlers"
        ag_file = os.path.join(base_path, "AG", "daily", "AG_fut_close.csv")

        if os.path.exists(ag_file):
            df = pd.read_csv(ag_file, encoding="utf-8-sig")
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date").sort_index()
            df["return_1d"] = df["close"].pct_change()
            df["return_5d"] = df["close"].pct_change(5)
            print(f"\n[AG数据] {len(df)} 行，日期范围: {df.index[0]} ~ {df.index[-1]}")

            # 2.1 滚动IC
            print("\n[2.1] 滚动IC/IR计算...")
            ic_calc = RollingICCalculator(window=60, min_periods=30)
            rolling_ic = ic_calc.compute_rolling_ic(df["close"], df["return_5d"])
            ic_stats = ic_calc.compute_ic_stats(rolling_ic)
            print(f"IC统计: mean={ic_stats['mean']:.4f}, IR={ic_stats['ir']:.4f}, "
                  f"t={ic_stats['t_stat']:.2f}, 胜率={ic_stats['win_rate']:.1%}")

            # 2.2 Bootstrap CI
            print("\n[2.2] Bootstrap置信区间...")
            bs = BootstrapAnalyzer(n_bootstrap=1000, random_state=42)
            ci_result = bs.compute_ic_ci(df["close"], df["return_5d"])
            print(f"IC均值: {ci_result['ic_mean']:.4f}")
            print(f"95% CI: [{ci_result['ci_lower']:.4f}, {ci_result['ci_upper']:.4f}]")
            print(f"显著性: {'是' if ci_result['significant'] else '否'}")

            # 2.3 HMM
            print("\n[2.3] HMM市场状态检测 (hmmlearn)...")
            hmm = HMMRegimeDetector(n_regimes=3, random_state=42)
            try:
                hmm.fit(df["return_1d"])
                regime_stats = hmm.get_regime_stats()
                print(f"检测到 {len(regime_stats)} 个市场状态:")
                for regime, stats in regime_stats.items():
                    print(f"  {regime}: 占比{stats['pct']:.1%}, "
                          f"平均收益{stats['mean_return']:.6f}")
                print("转移矩阵:")
                print(hmm.get_transition_matrix())
            except Exception as e:
                print(f"HMM拟合失败: {e}")

            # 2.4 因子衰减
            print("\n[2.4] 因子衰减分析...")
            decay = FactorDecayAnalyzer(max_lag=10)
            decay_curve = decay.compute_decay_curve(df["close"], df["return_1d"])
            half_life = decay.compute_half_life(decay_curve)
            print(f"IC衰减曲线 (lag 1-5): {[f'{v:.4f}' for v in decay_curve.head(5).values]}")
            print(f"半衰期: {half_life} 天")
        else:
            print(f"\n[AG数据文件不存在: {ag_file}]")

        # 2.5 PIT数据服务演示
        print("\n[2.5] PIT数据服务...")
        try:
            with PITDataService() as pit:
                factors = pit.list_factors(is_active=True, frequency="daily")
                print(f"活跃日频因子数: {len(factors)}")
                pit_check = pit.verify_pit_compliance("jm_futures_spread")
                print(f"JM spread PIT合规: {pit_check['compliant']}, "
                      f"未来违规: {pit_check['future_violations']}")
        except Exception as e:
            print(f"PIT查询失败: {e}")

    print("\n" + "=" * 80)
    print("Phase 2 hmmlearn+PIT 版本完成")
    print("=" * 80)
