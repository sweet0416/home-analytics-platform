const sourceLabels: Record<string, string> = {
  sporttery: '中国体育彩票（官方）',
  '500_lottery': '500 彩票（备用）',
  automatic: '自动选择',
};

export function lotterySyncSourceLabel(source: string): string {
  return sourceLabels[source] ?? source;
}

export function lotterySyncSourceDescription(source: string | undefined): string {
  if (source === 'sporttery') return '来自中国体育彩票公开数据';
  if (source === '500_lottery') return '来自 500 彩票公开历史数据（第三方备用）';
  return '官方源优先，异常时自动切换备用源';
}
