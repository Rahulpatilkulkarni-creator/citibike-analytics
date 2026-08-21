import pandas as pd
from scipy import stats

df = pd.read_csv("daily_rides_weather.csv")
df['ride_date'] = pd.to_datetime(df['ride_date'])

print(f"Loaded {len(df)} days of data.\n")

# ---- Correlation: temperature vs ride volume, by rider type ----
member_temp_corr, member_temp_p = stats.pearsonr(df['temp_mean_c'], df['member_rides'])
casual_temp_corr, casual_temp_p = stats.pearsonr(df['temp_mean_c'], df['casual_rides'])
print("=== Temperature Correlation ===")
print(f"Member rides vs temp:  r = {member_temp_corr:.3f}  (p = {member_temp_p:.5f})")
print(f"Casual rides vs temp:  r = {casual_temp_corr:.3f}  (p = {casual_temp_p:.5f})")
# ---- Correlation: precipitation vs ride volume, by rider type ----
member_precip_corr, member_precip_p = stats.pearsonr(df['precipitation_mm'], df['member_rides'])
casual_precip_corr, casual_precip_p = stats.pearsonr(df['precipitation_mm'], df['casual_rides'])
print("\n=== Precipitation Correlation ===")
print(f"Member rides vs rain:  r = {member_precip_corr:.3f}  (p = {member_precip_p:.5f})")
print(f"Casual rides vs rain:  r = {casual_precip_corr:.3f}  (p = {casual_precip_p:.5f})")
# ---- Direct comparison: rainy days vs dry days, average rides ----
df['is_rainy'] = df['precipitation_mm'] > 5  # more than 5mm = a genuinely wet day
rainy_member_avg = df[df['is_rainy']]['member_rides'].mean()
dry_member_avg = df[~df['is_rainy']]['member_rides'].mean()
rainy_casual_avg = df[df['is_rainy']]['casual_rides'].mean()
dry_casual_avg = df[~df['is_rainy']]['casual_rides'].mean()

print("\n=== Rainy Day (>5mm) vs Dry Day Averages ===")
print(f"Member rides  - dry: {dry_member_avg:.0f}  |  rainy: {rainy_member_avg:.0f}  |  drop: {100*(1 - rainy_member_avg/dry_member_avg):.1f}%")
print(f"Casual rides  - dry: {dry_casual_avg:.0f}  |  rainy: {rainy_casual_avg:.0f}  |  drop: {100*(1 - rainy_casual_avg/dry_casual_avg):.1f}%")


# t-test: is the rainy-day drop statistically significant for each group?
member_ttest = stats.ttest_ind(df[df['is_rainy']]['member_rides'], df[~df['is_rainy']]['member_rides'])
casual_ttest = stats.ttest_ind(df[df['is_rainy']]['casual_rides'], df[~df['is_rainy']]['casual_rides'])

print(f"\nMember rainy-vs-dry t-test:  t = {member_ttest.statistic:.2f}, p = {member_ttest.pvalue:.5f}")
print(f"Casual rainy-vs-dry t-test:  t = {casual_ttest.statistic:.2f}, p = {casual_ttest.pvalue:.5f}")