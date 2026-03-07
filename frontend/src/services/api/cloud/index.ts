import announcement from './announcement'
import auth from './auth'
import { pluginsMarketApi } from './plugins_market'
import { presetsMarketApi } from './presets_market'
import { telemetryApi } from './telemetry'

// Auth API
export const authApi = {
  checkGitHubStars: auth.checkGitHubStars,
  getCommunityUserProfile: auth.getCommunityUserProfile,
}

export const cloudApi = {
  auth,
  announcement,
  plugins: pluginsMarketApi,
  presets: presetsMarketApi,
  telemetry: telemetryApi,
}
