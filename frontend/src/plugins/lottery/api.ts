import { getApiData } from '@/api/client';

export interface PrizeTier {
  tier: number;
  tier_name: string;
  front_match_count: number;
  back_match_count: number;
  is_floating: boolean;
  base_prize_amount: string | null;
  addon_multiplier: string | null;
  description: string;
}

export interface LotteryRule {
  rule_code: string;
  rule_name: string;
  game_code: string;
  front: {
    count: number;
    min: number;
    max: number;
  };
  back: {
    count: number;
    min: number;
    max: number;
  };
  base_price: string;
  addon_price: string;
  addon_supported: boolean;
  official_url: string;
  prize_tiers: PrizeTier[];
}

export interface LotteryDraw {
  issue_no: string;
  draw_date: string;
  front_numbers: number[];
  back_numbers: number[];
  sales_amount: string | null;
  pool_amount: string | null;
  source_url: string | null;
}

export interface DrawPage {
  items: LotteryDraw[];
  pagination: {
    page: number;
    page_size: number;
    total: number;
    pages: number;
  };
}

export function fetchCurrentRule(): Promise<LotteryRule> {
  return getApiData<LotteryRule>('/lottery/dlt/rules/current');
}

export function fetchDraws(): Promise<DrawPage> {
  return getApiData<DrawPage>('/lottery/dlt/draws?page=1&page_size=20');
}

export function fetchDisclaimer(): Promise<{ disclaimer: string }> {
  return getApiData<{ disclaimer: string }>('/lottery/dlt/disclaimer');
}

