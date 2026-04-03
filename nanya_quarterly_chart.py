import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

# Nanya Technology (2408.TW) Quarterly Financial Data
# Source: stockanalysis.com

quarters = [
    'Q1\n2023', 'Q2\n2023', 'Q3\n2023', 'Q4\n2023',
    'Q1\n2024', 'Q2\n2024', 'Q3\n2024', 'Q4\n2024',
    'Q1\n2025', 'Q2\n2025', 'Q3\n2025', 'Q4\n2025',
]

# Revenue (NT$ billions)
revenue = [6.42, 7.03, 7.74, 8.70, 9.50, 9.92, 8.13, 6.58, 7.19, 10.53, 18.78, 30.09]

# Operating Income (NT$ billions)
operating_income = [-2.89, -3.18, -4.34, -4.05, -2.92, -2.32, -2.51, -2.81, -3.16, -4.50, 1.12, 11.78]

# Net Income (NT$ billions)
net_income = [-1.68, -0.77, -2.50, -2.48, -1.21, -0.81, -1.49, -1.57, -1.94, -4.10, 1.56, 11.09]

# Margins (%)
gross_margin = [-8.6, -11.2, -25.2, -13.6, -2.9, 2.9, 3.2, -10.6, -15.0, -20.6, 18.4, 49.0]
operating_margin = [-44.9, -45.3, -56.1, -46.5, -30.7, -23.4, -30.8, -42.8, -43.9, -42.8, 6.0, 39.1]
net_margin = [-26.2, -11.0, -32.4, -28.5, -12.7, -8.2, -18.3, -23.9, -27.0, -39.0, 8.3, 36.9]

x = np.arange(len(quarters))
width = 0.28

# Create figure with 2 subplots
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12), gridspec_kw={'height_ratios': [1.2, 1]})
fig.suptitle('Nanya Technology (2408.TW) Quarterly Earnings Summary\n2023 Q1 ~ 2025 Q4',
             fontsize=18, fontweight='bold', y=0.98)

# --- Top Chart: Revenue, Operating Income, Net Income (Bar Chart) ---
bars1 = ax1.bar(x - width, revenue, width, label='Revenue', color='#4A90D9', edgecolor='white', linewidth=0.5)
bars2 = ax1.bar(x, operating_income, width, label='Operating Income', color='#E8833A', edgecolor='white', linewidth=0.5)
bars3 = ax1.bar(x + width, net_income, width, label='Net Income', color='#50B88E', edgecolor='white', linewidth=0.5)

ax1.set_ylabel('NT$ Billions', fontsize=13, fontweight='bold')
ax1.set_xticks(x)
ax1.set_xticklabels(quarters, fontsize=9)
ax1.legend(fontsize=11, loc='upper left')
ax1.axhline(y=0, color='black', linewidth=0.8, linestyle='-')
ax1.set_title('Revenue / Operating Income / Net Income', fontsize=14, pad=10)
ax1.grid(axis='y', alpha=0.3)

# Annotate the dramatic Q4 2025 values
ax1.annotate(f'{revenue[-1]:.1f}B', xy=(x[-1] - width, revenue[-1]),
             xytext=(0, 5), textcoords='offset points', ha='center', fontsize=8, fontweight='bold', color='#4A90D9')
ax1.annotate(f'{operating_income[-1]:.1f}B', xy=(x[-1], operating_income[-1]),
             xytext=(0, 5), textcoords='offset points', ha='center', fontsize=8, fontweight='bold', color='#E8833A')
ax1.annotate(f'{net_income[-1]:.1f}B', xy=(x[-1] + width, net_income[-1]),
             xytext=(0, 5), textcoords='offset points', ha='center', fontsize=8, fontweight='bold', color='#50B88E')

# Add shaded regions for each year
for i, year in enumerate(['2023', '2024', '2025']):
    ax1.axvspan(i*4 - 0.5, i*4 + 3.5, alpha=0.05, color=['blue', 'orange', 'green'][i])

# --- Bottom Chart: Margin Trends (Line Chart) ---
ax2.plot(x, gross_margin, 'o-', label='Gross Margin', color='#4A90D9', linewidth=2.5, markersize=6)
ax2.plot(x, operating_margin, 's-', label='Operating Margin', color='#E8833A', linewidth=2.5, markersize=6)
ax2.plot(x, net_margin, '^-', label='Net Margin', color='#50B88E', linewidth=2.5, markersize=6)

ax2.set_ylabel('Margin (%)', fontsize=13, fontweight='bold')
ax2.set_xticks(x)
ax2.set_xticklabels(quarters, fontsize=9)
ax2.legend(fontsize=11, loc='upper left')
ax2.axhline(y=0, color='black', linewidth=1.2, linestyle='--')
ax2.set_title('Gross / Operating / Net Margin Trends', fontsize=14, pad=10)
ax2.grid(axis='y', alpha=0.3)
ax2.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.0f%%'))

# Annotate Q4 2025 margin values
for val, label, color, offset in [
    (gross_margin[-1], f'{gross_margin[-1]:.1f}%', '#4A90D9', 10),
    (operating_margin[-1], f'{operating_margin[-1]:.1f}%', '#E8833A', -15),
    (net_margin[-1], f'{net_margin[-1]:.1f}%', '#50B88E', -12),
]:
    ax2.annotate(label, xy=(x[-1], val), xytext=(8, offset), textcoords='offset points',
                 fontsize=9, fontweight='bold', color=color,
                 arrowprops=dict(arrowstyle='->', color=color, lw=1.2))

# Add shaded regions for each year
for i in range(3):
    ax2.axvspan(i*4 - 0.5, i*4 + 3.5, alpha=0.05, color=['blue', 'orange', 'green'][i])

# Add AI/HBM narrative annotation
ax2.annotate('AI/HBM demand\ndrives turnaround →',
             xy=(9.5, -30), fontsize=10, fontstyle='italic', color='#C0392B',
             fontweight='bold',
             bbox=dict(boxstyle='round,pad=0.4', facecolor='#FDEBD0', edgecolor='#E8833A', alpha=0.8))

plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig('/home/user/conference-call-notion-bot/nanya_quarterly_earnings.png', dpi=150, bbox_inches='tight')
print("Chart saved: nanya_quarterly_earnings.png")
