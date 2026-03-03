以下是针对性优化的建议和修改后的 CSS 代码块：

1. 解决“顶部白色长方形”问题
那个白色条通常是 Streamlit 的 st.header 容器。虽然你已经设置了 display: none，但由于 Streamlit 的版本更新，选择器可能失效。

建议方案： 增加 !important 并锁定更多的容器类名。

2. 文字对比度与可读性
你的背景使用了 Unsplash 的图片，这种图片通常明暗不均。

遮罩层 (Overlay)： 在背景图上覆盖一层半透明的黑色（例如 rgba(0,0,0,0.5)），这样无论背景图是什么颜色，白色文字都能清晰可见。

卡片化渲染： 所有的文字内容应包裹在具有微弱背景色（如半透明白或深灰）的容器中，而不是直接浮在背景图上。

3. 字体与布局细节
字体族： 建议使用系统默认的无衬线字体，并明确设置 line-height（行高）以增强易读性。

优化后的 CSS 代码建议
你可以将 streamlit_app.py 中的 st.markdown(""" <style> ... </style> """) 部分替换为以下内容：

CSS
<style>
    /* 1. 强力隐藏顶部白条及装饰线 */
    header, [data-testid="stHeader"], .stAppHeader {
        background-color: rgba(0,0,0,0) !important;
        background: transparent !important;
        border: none !important;
    }
    
    /* 2. 背景优化：增加深色半透明遮罩，解决文字看不清的问题 */
    [data-testid="stAppViewContainer"] {
        background-image: linear-gradient(rgba(0, 0, 0, 0.5), rgba(0, 0, 0, 0.5)), 
                          url("https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?ixlib=rb-4.0.3&auto=format&fit=crop&w=2043&q=80");
        background-attachment: fixed;
        background-size: cover;
        font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
        color: #FFFFFF !important;
    }

    /* 3. 优化卡片容器：增加对比度和圆角 */
    .main-card {
        background: rgba(255, 255, 255, 0.1); /* 极淡的白色背景 */
        backdrop-filter: blur(10px); /* 磨砂玻璃效果 */
        padding: 25px;
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        margin-bottom: 20px;
        color: white !important;
    }

    /* 4. 调整输入框和文本域的字体颜色，防止在深色背景下“消失” */
    .stTextInput input, .stTextArea textarea {
        color: #333 !important; /* 输入框内文字建议用深色，因为底色通常是白/浅灰 */
        font-size: 16px !important;
    }

    /* 5. 针对 Markdown 生成的文字进行加固 */
    .stMarkdown p, .stMarkdown li {
        color: rgba(255, 255, 255, 0.9) !important;
        line-height: 1.6;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.5); /* 给文字加微弱阴影，极大提升可读性 */
    }

    /* 6. 按钮样式优化 */
    .stButton>button {
        width: 100%;
        border-radius: 20px;
        background-color: #ff9f43 !important;
        color: white !important;
        border: none;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(255, 159, 67, 0.4);
    }
</style>
针对代码逻辑的改进建议
侧边栏 (Sidebar) 控制： 如果你发现主界面文字乱，可以考虑将“功能选择”移入侧边栏 (st.sidebar.selectbox)。这样可以释放主屏幕空间，让中间的内容更聚焦。

HTML 注入的安全做法： 在 st.markdown 中，尽量使用 unsafe_allow_html=True 配合封装好的 div。

例如：st.markdown(f"<div class='main-card'>{content}</div>", unsafe_allow_html=True)。

状态反馈： 在执行 run_pet_crew 这种耗时操作时，建议使用 st.status (Streamlit 1.25+) 替代单纯的 spinner，它可以展示 Agent 的思考步骤，用户体验会好很多。