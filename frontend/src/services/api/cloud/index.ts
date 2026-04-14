import announcement from './announcement'
import auth from './auth'
import { favoritesApi } from './favorites'
import { pluginsMarketApi } from './plugins_market'
import { presetsMarketApi } from './presets_market'
import { telemetryApi } from './telemetry'

// Auth API
export const authApi = {
  checkGitHubStars: auth.checkGitHubStars,
  getCommunityUserProfile: auth.getCommunityUserProfile,
}

export { favoritesApi }

export const cloudApi = {
  auth,
  announcement,
  plugins: pluginsMarketApi,
  presets: presetsMarketApi,
  telemetry: telemetryApi,
  favorites: favoritesApi,
}
