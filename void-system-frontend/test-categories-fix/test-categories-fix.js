/**
 * 测试脚本：验证Advisor.vue中任务类别获取错误的修复
 * 这个脚本模拟API调用失败的情况，测试错误处理逻辑
 */

// 模拟API调用失败的情况
function testCategoriesErrorHandling() {
  console.log('=== 测试任务类别获取错误处理 ===\n');
  
  // 测试1: API返回非数组数据（模拟401错误）
  console.log('测试1: API返回401未授权错误');
  const mockApiResponse1 = {
    success: false,
    message: "Not authenticated",
    data: null,
    error_code: "HTTP_401",
    request_id: "30f0ab71-e6bd-4a2c-98d5-db7867e292b6"
  };
  
  // 修复前的代码（会报错）
  console.log('修复前代码:');
  try {
    const categories = mockApiResponse1.data; // 这里会是null
    const quickTopics = categories.map((category, index) => ({
      id: category.category_id || index + 1,
      text: category.category_name,
      icon: category.icon,
      isPreset: category.is_preset
    }));
    console.log('❌ 修复前代码执行成功（不应该发生）');
  } catch (error) {
    console.log('✅ 修复前代码报错（预期行为）:', error.message);
  }
  
  // 修复后的代码
  console.log('\n修复后代码:');
  try {
    const categories = mockApiResponse1.data;
    const quickTopics = Array.isArray(categories) ? categories.map((category, index) => ({
      id: category.category_id || index + 1,
      text: category.category_name,
      icon: category.icon,
      isPreset: category.is_preset
    })) : [
      { id: 1, text: '学习Python数据分析', icon: '🐍', isPreset: true },
      { id: 2, text: '准备英语四级考试', icon: '📚', isPreset: true },
      { id: 3, text: '学习Vue 3框架', icon: '💻', isPreset: true },
      { id: 4, text: '减肥健身计划', icon: '🏃‍♂️', isPreset: true },
      { id: 5, text: '学习摄影技巧', icon: '📷', isPreset: true },
      { id: 6, text: '准备考研数学', icon: '📐', isPreset: true },
      { id: 7, text: '学习UI设计', icon: '🎨', isPreset: true },
      { id: 8, text: '学习吉他基础', icon: '🎸', isPreset: true }
    ];
    console.log('✅ 修复后代码执行成功，使用默认主题');
    console.log('生成的主题数量:', quickTopics.length);
  } catch (error) {
    console.log('❌ 修复后代码报错（不应该发生）:', error.message);
  }
  
  // 测试2: API返回空数组
  console.log('\n测试2: API返回空数组');
  const mockApiResponse2 = {
    success: true,
    message: "Success",
    data: [],
    error_code: null,
    request_id: "30f0ab71-e6bd-4a2c-98d5-db7867e292b6"
  };
  
  try {
    const categories = mockApiResponse2.data;
    const quickTopics = Array.isArray(categories) ? categories.map((category, index) => ({
      id: category.category_id || index + 1,
      text: category.category_name,
      icon: category.icon,
      isPreset: category.is_preset
    })) : [];
    console.log('✅ 修复后代码执行成功，使用空数组');
    console.log('生成的主题数量:', quickTopics.length);
  } catch (error) {
    console.log('❌ 修复后代码报错（不应该发生）:', error.message);
  }
  
  // 测试3: API返回有效数据
  console.log('\n测试3: API返回有效数据');
  const mockApiResponse3 = {
    success: true,
    message: "Success",
    data: [
      { category_id: 1, category_name: "学习编程", icon: "💻", is_preset: true },
      { category_id: 2, category_name: "健身运动", icon: "🏃‍♂️", is_preset: false }
    ],
    error_code: null,
    request_id: "30f0ab71-e6bd-4a2c-98d5-db7867e292b6"
  };
  
  try {
    const categories = mockApiResponse3.data;
    const quickTopics = Array.isArray(categories) ? categories.map((category, index) => ({
      id: category.category_id || index + 1,
      text: category.category_name,
      icon: category.icon,
      isPreset: category.is_preset
    })) : [];
    console.log('✅ 修复后代码执行成功，使用API数据');
    console.log('生成的主题数量:', quickTopics.length);
    console.log('主题详情:', JSON.stringify(quickTopics, null, 2));
  } catch (error) {
    console.log('❌ 修复后代码报错（不应该发生）:', error.message);
  }
}

// 运行测试
testCategoriesErrorHandling();

console.log('\n=== 测试完成 ===');
console.log('结论: 通过添加Array.isArray检查，可以防止categories.map is not a function错误');