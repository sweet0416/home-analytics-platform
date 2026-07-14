import { defineStore } from 'pinia';

import { fetchCurrentRule, fetchDisclaimer, fetchDraws, type DrawPage, type LotteryRule } from './api';

export const useLotteryStore = defineStore('lottery', {
  state: () => ({
    rule: null as LotteryRule | null,
    draws: null as DrawPage | null,
    disclaimer: '',
    loading: false,
    error: '',
  }),
  actions: {
    async loadOverview(): Promise<void> {
      this.loading = true;
      this.error = '';
      try {
        const [rule, draws, disclaimer] = await Promise.all([
          fetchCurrentRule(),
          fetchDraws(),
          fetchDisclaimer(),
        ]);
        this.rule = rule;
        this.draws = draws;
        this.disclaimer = disclaimer.disclaimer;
      } catch (error) {
        this.error = error instanceof Error ? error.message : 'Failed to load lottery data';
      } finally {
        this.loading = false;
      }
    },
  },
});

