/**
 * 高级渐变工具
 * 提供更现代的CSS渐变效果，解决渐变断层问题
 */
import { alpha } from '@mui/material/styles'

// 添加微噪点纹理到渐变中以消除色带
const noiseTexture = `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.05'/%3E%3C/svg%3E")`

/**
 * 高级渐变生成器
 * 使用现代CSS特性创建更平滑的渐变效果
 */
export const AdvancedGradients = {
  /**
   * 创建平滑背景渐变
   * @param color 基础颜色
   * @param mode 主题模式
   * @param opacity 基础不透明度
   * @returns CSS渐变字符串
   */
  smoothBackground: (color: string, mode: 'light' | 'dark', opacity: number = 0.9): string => {
    // 使用径向渐变和多层渐变组合，避免明显的条纹
    return `
      radial-gradient(circle at 0% 0%, ${alpha(color, opacity - 0.05)} 0%, transparent 50%),
      radial-gradient(circle at 100% 0%, ${alpha(color, opacity - 0.08)} 0%, transparent 50%),
      radial-gradient(circle at 100% 100%, ${alpha(color, opacity - 0.03)} 0%, transparent 50%),
      radial-gradient(circle at 0% 100%, ${alpha(color, opacity - 0.07)} 0%, transparent 50%),
      ${mode === 'dark' 
        ? `linear-gradient(135deg, ${alpha(color, opacity)} 0%, ${alpha(color, opacity - 0.1)} 100%)`
        : `linear-gradient(135deg, ${alpha(color, opacity - 0.05)} 0%, ${alpha(color, opacity)} 100%)`
      },
      ${noiseTexture}
    `
  },

  /**
   * 创建平滑卡片渐变
   * @param color 基础颜色
   * @param mode 主题模式
   * @returns CSS渐变字符串
   */
  smoothCard: (color: string, mode: 'light' | 'dark'): string => {
    if (mode === 'light') {
      return `
        linear-gradient(145deg, rgba(255, 255, 255, 0.92), ${alpha(color, 0.03)} 120%),
        ${noiseTexture}
      `
    }
    return `
      linear-gradient(145deg, ${alpha(color, 0.12)} -20%, ${alpha(color, 0.03)} 60%),
      ${noiseTexture}
    `
  },

  /**
   * 创建主题色渐变按钮
   * @param color 主色调
   * @returns CSS渐变字符串
   */
  buttonGradient: (color: string): string => {
    // 使用锥形渐变(conic-gradient)创建更动态的按钮效果
    return `
      linear-gradient(135deg, ${color} 0%, ${alpha(color, 0.85)} 100%),
      ${noiseTexture}
    `
  },

  /**
   * 创建全息效果渐变
   * @param color 主色调
   * @param secondaryColor 辅助色调
   * @returns CSS渐变字符串
   */
  holographic: (color: string, secondaryColor: string): string => {
    // 使用多层渐变和模糊效果创建全息效果
    return `
      linear-gradient(45deg, ${alpha(color, 0.4)} 0%, transparent 40%),
      linear-gradient(135deg, ${alpha(secondaryColor, 0.4)} 10%, transparent 50%),
      linear-gradient(225deg, ${alpha(color, 0.4)} 20%, transparent 60%),
      linear-gradient(315deg, ${alpha(secondaryColor, 0.4)} 30%, transparent 70%),
      ${noiseTexture}
    `
  },

  /**
   * 创建磨砂玻璃效果背景
   * 需要与backdrop-filter结合使用
   * @param color 基础颜色
   * @param opacity 不透明度
   * @returns CSS背景字符串
   */
  frostedGlass: (color: string, opacity: number = 0.7): string => {
    // 磨砂玻璃效果，配合backdrop-filter使用
    return `
      linear-gradient(135deg, ${alpha(color, opacity)} 0%, ${alpha(color, opacity - 0.2)} 100%),
      ${noiseTexture}
    `
  },

  /**
   * 创建动态网格背景
   * @param primaryColor 主色调
   * @param secondaryColor 辅助色调 
   * @param mode 主题模式
   * @returns CSS背景字符串
   */
  meshGradient: (primaryColor: string, secondaryColor: string, mode: 'light' | 'dark'): string => {
    const baseOpacity = mode === 'light' ? 0.05 : 0.1
    
    // 使用径向渐变创建网格效果
    return `
      radial-gradient(circle at 25% 25%, ${alpha(primaryColor, baseOpacity + 0.05)} 0%, transparent 50%),
      radial-gradient(circle at 75% 75%, ${alpha(secondaryColor, baseOpacity + 0.05)} 0%, transparent 50%),
      radial-gradient(circle at 75% 25%, ${alpha(primaryColor, baseOpacity)} 0%, transparent 40%),
      radial-gradient(circle at 25% 75%, ${alpha(secondaryColor, baseOpacity)} 0%, transparent 40%),
      ${mode === 'light' ? 'white' : '#121212'},
      ${noiseTexture}
    `
  }
}

/**
 * 高级背景样式
 * 提供完整的CSS样式对象，包括渐变和其他相关属性
 */
export const AdvancedBackgrounds = {
  /**
   * 磨砂卡片样式
   * @param color 基础颜色
   * @param mode 主题模式
   */
  frostedCard: (color: string, mode: 'light' | 'dark') => {
    return {
      background: AdvancedGradients.frostedGlass(color, mode === 'light' ? 0.8 : 0.6),
      backdropFilter: 'blur(10px)',
      WebkitBackdropFilter: 'blur(10px)',
      borderRadius: '8px',
      border: `1px solid ${alpha(color, mode === 'light' ? 0.1 : 0.15)}`,
    }
  },

  /**
   * 现代容器样式
   * @param color 基础颜色
   * @param mode 主题模式
   */
  modernContainer: (color: string, mode: 'light' | 'dark') => {
    return {
      background: AdvancedGradients.smoothBackground(color, mode),
      backdropFilter: 'blur(8px)',
      WebkitBackdropFilter: 'blur(8px)',
      borderRadius: '8px',
      border: `1px solid ${alpha(color, mode === 'light' ? 0.08 : 0.12)}`,
      boxShadow: mode === 'light'
        ? '0 4px 20px rgba(0, 0, 0, 0.08)'
        : '0 4px 20px rgba(0, 0, 0, 0.3)',
    }
  },

  /**
   * 高光按钮样式
   * @param color 主色调
   */
  glowButton: (color: string) => {
    return {
      background: AdvancedGradients.buttonGradient(color),
      boxShadow: `0 0 15px ${alpha(color, 0.5)}`,
      border: 'none',
      color: '#fff',
      transition: 'all 0.3s ease',
      '&:hover': {
        boxShadow: `0 0 20px ${alpha(color, 0.7)}`,
        transform: 'translateY(-2px)',
      }
    }
  }
}

// 为CSS Houdini API定义接口类型
interface CSSPaintWorklet {
  addModule(moduleURL: string): Promise<void>;
}

interface ExtendedCSS extends Omit<typeof CSS, 'supports'> {
  paintWorklet?: CSSPaintWorklet;
  supports: typeof CSS.supports;
}

/**
 * CSS Houdini Paint API 注册函数
 * 注意：这需要浏览器支持CSS Houdini
 * 可以用于创建更高级的自定义渐变效果
 */
export const registerHoudiniPaints = () => {
  if (typeof window !== 'undefined' && 'CSS' in window) {
    try {
      // 使用更精确的类型定义
      const css = window.CSS as ExtendedCSS;
      if (css.paintWorklet) {
        // 注册噪点渐变工作流
        css.paintWorklet.addModule(
          'data:application/javascript;base64,cmVnaXN0ZXJQYWludCgnbm9pc2UtZ3JhZGllbnQnLCBjbGFzcyB7CiAgc3RhdGljIGdldCBpbnB1dFByb3BlcnRpZXMoKSB7IHJldHVybiBbJy0tbm9pc2Utb3BhY2l0eSddOyB9CiAgcGFpbnQoY3R4LCBnZW9tLCBwcm9wZXJ0aWVzKSB7CiAgICBjb25zdCBub2lzZU9wYWNpdHkgPSBwcm9wZXJ0aWVzLmdldCgnLS1ub2lzZS1vcGFjaXR5JykgfHwgMC4wNTsKICAgIGNvbnN0IHdpZHRoID0gZ2VvbS53aWR0aDsKICAgIGNvbnN0IGhlaWdodCA9IGdlb20uaGVpZ2h0OwogICAgZm9yIChsZXQgeCA9IDA7IHggPCB3aWR0aDsgeCsrKSB7CiAgICAgIGZvciAobGV0IHkgPSAwOyB5IDwgaGVpZ2h0OyB5KyspIHsKICAgICAgICBpZiAoTWF0aC5yYW5kb20oKSA8IDAuMSkgewogICAgICAgICAgY3R4LmZpbGxTdHlsZSA9IGByZ2JhKDI1NSwgMjU1LCAyNTUsICR7TWF0aC5yYW5kb20oKSAqIG5vaXNlT3BhY2l0eX0pYDsKICAgICAgICAgIGN0eC5maWxsUmVjdCh4LCB5LCAxLCAxKTsKICAgICAgICB9CiAgICAgIH0KICAgIH0KICB9Cn0pOw=='
        );
        console.log('Noise gradient paint worklet registered');
      }
    } catch (e) {
      console.warn('Could not register CSS Houdini paint worklets', e);
    }
  }
}

export default AdvancedGradients; 