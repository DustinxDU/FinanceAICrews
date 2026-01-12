import { LLMProviderInfo, CreateLLMConfigRequest } from './api';

// 验证规则接口
export interface ValidationRule {
  required?: boolean;
  minLength?: number;
  maxLength?: number;
  pattern?: RegExp;
  custom?: (value: any, formData?: CreateLLMConfigRequest, provider?: LLMProviderInfo) => string | null;
  message?: string;
}

// 验证结果接口
export interface ValidationResult {
  isValid: boolean;
  errors: Record<string, string>;
}

// 字段验证规则配置
export const validationRules: Record<string, ValidationRule> = {
  provider: {
    required: true,
    message: "请选择提供商",
  },
  display_name: {
    required: true,
    minLength: 2,
    maxLength: 100,
    pattern: /^[a-zA-Z0-9\u4e00-\u9fa5\s\-_]+$/,
    custom: (value) => {
      if (!value || value.trim().length < 2) {
        return "配置名称至少需要2个字符";
      }
      if (value.length > 100) {
        return "配置名称不能超过100个字符";
      }
      if (!/^[a-zA-Z0-9\u4e00-\u9fa5\s\-_]+$/.test(value)) {
        return "配置名称只能包含字母、数字、中文、空格、连字符和下划线";
      }
      return null;
    },
    message: "请输入有效的配置名称",
  },
  api_key: {
    required: true,
    minLength: 10,
    maxLength: 500,
    pattern: /^[a-zA-Z0-9\-_\.]+$/,
    custom: (value) => {
      if (!value) return "请输入API密钥";
      if (value.length < 10) return "API密钥长度不足，至少需要10个字符";
      if (value.length > 500) return "API密钥过长";
      if (!/^[a-zA-Z0-9\-_\.]+$/.test(value)) {
        return "API密钥只能包含字母、数字、连字符、下划线和点";
      }
      return null;
    },
    message: "请输入有效的API密钥",
  },
  base_url: {
    required: false,
    pattern: /^https?:\/\/.+/,
    custom: (value, formData, provider) => {
      if (provider?.requires_base_url && !value) {
        return "该提供商需要配置Base URL";
      }
      if (value && !/^https?:\/\/.+/.test(value)) {
        return "Base URL必须以http://或https://开头";
      }
      return null;
    },
    message: "请输入有效的Base URL",
  },
  endpoint_id: {
    required: false,
    pattern: /^[a-zA-Z0-9\-_]+$/,
    custom: (value, formData, provider) => {
      if (provider?.requires_endpoint_id && !value) {
        return "该提供商需要Endpoint ID";
      }
      if (value && !/^[a-zA-Z0-9\-_]+$/.test(value)) {
        return "Endpoint ID只能包含字母、数字和连字符";
      }
      return null;
    },
    message: "请输入有效的Endpoint ID",
  },
  custom_model_name: {
    required: false,
    minLength: 1,
    maxLength: 100,
    pattern: /^[a-zA-Z0-9\-_\.]+$/,
    custom: (value, formData, provider) => {
      if (provider?.requires_custom_model_name && !value) {
        return "该提供商需要指定自定义模型名称";
      }
      if (value) {
        if (value.length > 100) {
          return "模型名称不能超过100个字符";
        }
        if (!/^[a-zA-Z0-9\-_\.]+$/.test(value)) {
          return "模型名称只能包含字母、数字、连字符、下划线和点";
        }
      }
      return null;
    },
    message: "请输入有效的自定义模型名称",
  },
  default_model: {
    required: false,
    minLength: 1,
    maxLength: 100,
    custom: (value) => {
      if (value && (value.length < 1 || value.length > 100)) {
        return "默认模型名称长度应在1-100个字符之间";
      }
      return null;
    },
    message: "请输入有效的默认模型名称",
  },
  temperature: {
    required: true,
    custom: (value) => {
      if (typeof value !== 'number' || isNaN(value)) {
        return "温度参数必须是数字";
      }
      if (value < 0 || value > 2) {
        return "温度参数应在0-2之间";
      }
      return null;
    },
    message: "温度参数应在0-2之间",
  },
  max_tokens: {
    required: false,
    custom: (value) => {
      if (value !== undefined && value !== null) {
        if (typeof value !== 'number' || isNaN(value)) {
          return "最大令牌数必须是数字";
        }
        if (value < 1 || value > 32000) {
          return "最大令牌数应在1-32000之间";
        }
      }
      return null;
    },
    message: "最大令牌数应在1-32000之间",
  },
};

// 实时验证函数
export const validateField = (
  fieldName: string,
  value: any,
  formData?: CreateLLMConfigRequest,
  provider?: LLMProviderInfo
): string | null => {
  const rule = validationRules[fieldName];
  if (!rule) return null;

  // 必填验证
  if (rule.required && (!value || (typeof value === 'string' && !value.trim()))) {
    return rule.message || `${fieldName}是必填字段`;
  }

  // 如果字段为空且不是必填的，跳过后续验证
  if (!value && !rule.required) {
    return null;
  }

  // 字符串类型验证
  if (typeof value === 'string') {
    // 长度验证
    if (rule.minLength && value.length < rule.minLength) {
      return rule.message || `${fieldName}长度不足`;
    }
    if (rule.maxLength && value.length > rule.maxLength) {
      return rule.message || `${fieldName}长度过长`;
    }

    // 正则验证
    if (rule.pattern && !rule.pattern.test(value)) {
      return rule.message || `${fieldName}格式不正确`;
    }
  }

  // 自定义验证
  if (rule.custom) {
    return rule.custom(value, formData, provider) || null;
  }

  return null;
};

// 完整表单验证
export const validateForm = (
  formData: CreateLLMConfigRequest,
  provider?: LLMProviderInfo
): ValidationResult => {
  const errors: Record<string, string> = {};
  let isValid = true;

  // 遍历所有验证规则
  Object.keys(validationRules).forEach(fieldName => {
    const value = formData[fieldName as keyof CreateLLMConfigRequest];
    const error = validateField(fieldName, value, formData, provider);
    
    if (error) {
      errors[fieldName] = error;
      isValid = false;
    }
  });

  return { isValid, errors };
};

// API密钥格式验证
export const validateApiKeyFormat = (apiKey: string, provider: string): string | null => {
  if (!apiKey) return "API密钥不能为空";

  switch (provider) {
    case 'openai':
      if (!apiKey.startsWith('sk-') || apiKey.length !== 51) {
        return "OpenAI API密钥格式不正确，应以sk-开头，共51个字符";
      }
      break;
    
    case 'anthropic':
      if (!apiKey.startsWith('sk-ant-') || apiKey.length < 90) {
        return "Anthropic API密钥格式不正确，应以sk-ant-开头";
      }
      break;
    
    case 'volcengine':
      // 火山引擎API密钥格式较为宽松，主要检查长度
      if (apiKey.length < 20) {
        return "火山引擎API密钥长度不足";
      }
      break;
    
    case 'baidu':
      // 百度API密钥通常有特定格式
      if (!/^[a-zA-Z0-9]{20,}$/.test(apiKey)) {
        return "百度API密钥格式不正确";
      }
      break;
    
    case 'alibaba':
      // 阿里云API密钥格式
      if (!/^[a-zA-Z0-9]{20,}$/.test(apiKey)) {
        return "阿里云API密钥格式不正确";
      }
      break;
    
    default:
      // 通用验证
      if (apiKey.length < 10) {
        return "API密钥长度不足";
      }
      break;
  }

  return null;
};

// URL验证
export const validateUrl = (url: string): string | null => {
  if (!url) return null;

  try {
    const urlObj = new URL(url);
    if (!['http:', 'https:'].includes(urlObj.protocol)) {
      return "URL必须是http或https协议";
    }
    return null;
  } catch {
    return "URL格式不正确";
  }
};

// 数值范围验证
export const validateNumberRange = (
  value: number,
  min: number,
  max: number,
  fieldName: string
): string | null => {
  if (typeof value !== 'number' || isNaN(value)) {
    return `${fieldName}必须是有效数字`;
  }
  if (value < min || value > max) {
    return `${fieldName}应在${min}-${max}之间`;
  }
  return null;
};

// 配置名称唯一性验证（模拟）
export const validateConfigNameUnique = async (
  name: string,
  excludeId?: string,
  existingConfigs?: any[]
): Promise<string | null> => {
  if (!name) return null;

  // 模拟API调用延迟
  await new Promise(resolve => setTimeout(resolve, 500));

  // 检查是否已存在相同名称的配置
  const exists = existingConfigs?.some(config => 
    config.display_name.toLowerCase() === name.toLowerCase() && 
    config.id !== excludeId
  );

  if (exists) {
    return "配置名称已存在，请使用其他名称";
  }

  return null;
};

// 验证状态类型
export interface ValidationState {
  isValidating: boolean;
  errors: Record<string, string>;
  lastValidated: number;
}

// 创建验证状态
export const createValidationState = (): ValidationState => ({
  isValidating: false,
  errors: {},
  lastValidated: 0,
});

// 验证工具函数
export class FormValidator {
  private validationState: ValidationState;

  constructor() {
    this.validationState = createValidationState();
  }

  getState(): ValidationState {
    return { ...this.validationState };
  }

  setValidating(isValidating: boolean) {
    this.validationState.isValidating = isValidating;
  }

  setErrors(errors: Record<string, string>) {
    this.validationState.errors = errors;
    this.validationState.lastValidated = Date.now();
  }

  clearErrors() {
    this.validationState.errors = {};
    this.validationState.lastValidated = Date.now();
  }

  hasErrors(): boolean {
    return Object.keys(this.validationState.errors).length > 0;
  }

  getError(fieldName: string): string | null {
    return this.validationState.errors[fieldName] || null;
  }
}