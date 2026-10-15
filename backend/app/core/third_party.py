"""本地第三方登录演示配置。"""

# 真实项目中授权码由微信临时签发，后端再向微信服务器换取 openid。
# 课程作业没有开放平台凭据，因此使用固定演示授权码模拟这次交换。
WECHAT_DEMO_AUTHORIZATION_CODE = "wechat_demo_authorized"
WECHAT_DEMO_OPENID = "wechat_demo_student001"

# QQ 登录同样使用本地演示授权码，绑定到测试教师账号。
QQ_DEMO_AUTHORIZATION_CODE = "qq_demo_authorized"
QQ_DEMO_OPENID = "qq_demo_teacher001"
