# -*- coding: utf-8 -*-
"""
Platform Personas - 定义各内容平台的用户群体画像
用于在 AI 生成视频文案和提示词时注入特定的风格和受众特征
"""

PERSONA_DOUYIN = """
### 抖音 (Douyin) 用户画像与内容风格：

**用户群体：**
*   **总体规模：** 国民级超级App，月活用户7.66亿+，日活用户超8亿。
*   **年龄分布：** 全龄覆盖（18-40岁为核心），银发族增长显著，短剧核心受众为中青年高收入群体。
*   **性别与偏好：** 男性52%/女性48%，用户喜爱精品短剧、AIGC创意、专业知识、本地生活服务内容。
*   **行为特征：** 短剧受众73%愿尝试新品牌，72%愿为品质消费，67%购前详细研究；算法分发沉浸成瘾。

**内容风格要求：**
1.  **精品化转型：** 应对完播率下降18%，必须走S级精品路线，拒绝"注水"内容。
2.  **前3秒生死局：** 算法极度惩罚开头拖沓，前3秒留存率权重最高。
3.  **AIGC深度融合：** 文生视频技术成为内容生产基建，需掌握即梦AI等工具。
4.  **情绪驱动与故事性：** 利用反转、剧情推进提升完播率；追求"真实美好"、"极致热爱"。
5.  **本地生活转化：** 不仅看CTR，更要看搜索主动性和本地生活服务转化效果。

**内容关键词：** 爆款、S级短剧、AIGC特效、本地生活探店、专业懂行、全域兴趣电商。
"""

PERSONA_KS = """
### 快手 (Kuaishou) 用户画像与内容风格：

**用户群体：**
*   **总体规模：** 月活用户7.31亿，3.4亿泛知识兴趣用户。
*   **年龄分布：** 24岁及以下年轻用户占比过半（>50%），是极度年轻化平台！Z世代与新线人群双重主导。
*   **地域与文化：** 新线城市（四线及以下）近7成用户，但数码消费TGI显著高于一线，是3C品牌"增量金矿"。
*   **兴趣偏好：** 用户偏好泛知识教程、连载短剧、游戏直播；8成用户每周观看短剧，日均时长同比增长17.2%。

**内容风格要求：**
1.  **泛知识布局：** 职业技能、农业技术、法律科普等实用型内容具有巨大市场。
2.  **信任关系第一：** 建立"人设"比制作精美"视频"更重要，老铁式沟通。
3.  **社群互动强：** 强调社区文化、多次互动建立信任，关注粉丝群活跃度和复购率。
4.  **连载粘性：** 短剧需强调高频更新和连载粘性。
5.  **故事叙述性：** 更长视频长度与叙事形式帮助建立用户粘性。

**内容关键词：** 老铁、泛知识教程、连载短剧、信任电商、技能分享、私域复购。
"""

PERSONA_XHS = """
### 小红书 (Xiaohongshu) 用户画像与内容风格：

**用户群体：**
*   **总体规模：** 月活用户3.5亿，已成为"国民生活决策搜索引擎"。
*   **性别分布：** 男性30%/女性70%（男性用户增速显著，科技/户外领域活跃）。
*   **年龄与城市分布：** 18-35岁年轻用户为核心，一线/新一线高线城市用户占比60%，全网最高客单价流量池。
*   **兴趣偏好：** 70%月活用户有搜索行为，88%搜索为主动发起，90%消费决策受搜索影响；高增长领域：出行旅游(+242%)、教育(+173%)、3C家电(+84%)。

**内容风格要求：**
1.  **SEO优先：** 内容从"展示"转向"解决问题"，关键词匹配度决定流量生死。
2.  **价值型内容：** 提供明确的种草理由、避坑指南或产品对比。
3.  **真实体验分享：** 亲测效果、细节说明与真实感受更具说服力。
4.  **结构化内容：** 使用标签与清晰段落提升搜索与复用价值，首图点击率决定成败。
5.  **情绪共鸣：** "去班味"、"松弛感"等心理代偿需求需被满足。

**内容关键词：** 真实测评、攻略教程、情绪Vlog、松弛感、主动搜索、品牌种草。
"""

PERSONA_WX = """
### 视频号 (WeChat Video) 用户画像与内容风格：

**用户群体：**
*   **总体规模：** 依托微信14亿用户生态，月活10亿+，日活8亿+。
*   **年龄分布：** 26-30岁职场青年占比43.7%成为绝对主力！银发族为第二峰值，形成"双主力"模型。
*   **社交传播特征：** 用户是"社交链条上的节点"，内容易于在微信朋友圈、群聊等私域传播，具有天然高信任基因。
*   **兴趣偏好：** 职场干货、品牌大事件、私域专属内容；偏好正能量、资讯性、深度内容与实用干货。

**内容风格要求：**
1.  **算法转向：** 推荐流量占比已达54.5%并将升至60%+，内容只需让用户"爱看"即可获推荐。
2.  **信息密度与深度：** 注重观点、洞察或实用资讯的解读。
3.  **完播率权重提升：** 降低"朋友点赞"冷启动权重，提升完播率和停留时长（对齐抖音逻辑）。
4.  **社交传播性：** 留足分享理由，私域导流、直播打赏为核心变现路径。
5.  **服务生态支持：** 可结合微信生态（公众号、小程序、私域社群）提升整体体验。

**内容关键词：** 职业发展、私域闭环、高客单价、品牌自播、社交裂变、信任转化。
"""

PERSONA_BILIBILI = """
### B站 (Bilibili) 用户画像与内容风格：

**用户群体：**
*   **总体规模：** 月活用户3.48亿，2亿用户观看科技视频。
*   **年龄分布：** 平均年龄24岁（大学毕业/职场新人），非"学生站"而是"年轻职场人社区"。
*   **性别与偏好：** 男性57%/女性43%，AI相关稿件超100万（00后占比60%），科技科普播放量增长200%。
*   **行为特征：** 高互动性（弹幕文化）、深度内容消费习惯、社区归属感强，是科技品牌必争之地。

**内容风格要求：**
1.  **中长视频护城河：** 坚持Video Essay价值，播放时长权重远高于点击。
2.  **弹幕互动设计：** 弹幕是核心互动指标，需设计弹幕互动点和梗点提升参与度。
3.  **硬核科技内容：** AI应用、深度科普、硬核评测是流量密码。
4.  **信息增量：** 避免过度娱乐化，强调内容的"深度"和"信息增量"。
5.  **高客单转化：** 汽车、数码、家电等高客单价评测内容转化影响力极高。

**内容关键词：** 硬核科技、深度科普、AI应用、一键三连、高能预警、内容带货。
"""

PLATFORM_PERSONAS = {
    "douyin": PERSONA_DOUYIN,
    "ks": PERSONA_KS,
    "xhs": PERSONA_XHS,
    "wx": PERSONA_WX,
    "bilibili": PERSONA_BILIBILI
}

PERSONA_DOUYIN_EN = """
### Douyin Audience Profile and Content Style:

**Audience Segments:**
*   **Overall Reach:** A national-scale super app with 766M+ monthly active users and 800M+ daily active users.
*   **Age Distribution:** Broad age coverage, with 18-40 as the core group; silver-haired users are growing quickly, while short-drama audiences skew toward middle-aged and young high-income users.
*   **Gender and Preferences:** Male 52% / female 48%; users respond well to premium short dramas, AIGC creativity, professional knowledge, and local-life service content.
*   **Behavior Signals:** Short-drama viewers are highly conversion-aware: 73% are willing to try new brands, 72% pay for quality, and 67% research carefully before purchase; algorithmic feeds create deep immersion.

**Content Style Requirements:**
1.  **Premium Execution:** With completion rates under pressure, content should pursue S-tier production quality and avoid padded or low-density storytelling.
2.  **First-3-Second Hook:** The algorithm heavily penalizes slow openings; early retention is the highest-priority signal.
3.  **Deep AIGC Integration:** Text-to-video and AI visual tools should be treated as core production infrastructure.
4.  **Emotion and Story Momentum:** Use reversals, narrative progression, and strong emotional stakes to improve completion.
5.  **Local-Life Conversion:** Optimize not only for CTR, but also for search intent and local service conversion.

**Content Keywords:** viral hit, S-tier short drama, AIGC effects, local-life discovery, professional authority, interest-based commerce.
"""

PERSONA_KS_EN = """
### Kuaishou Audience Profile and Content Style:

**Audience Segments:**
*   **Overall Reach:** 731M monthly active users, including 340M users interested in broad knowledge content.
*   **Age Distribution:** Users aged 24 and below account for more than half of the platform, making it strongly youth-oriented with both Gen Z and new-tier city audiences.
*   **Region and Culture:** Nearly 70% of users come from new-tier cities, including fourth-tier cities and below; digital product consumption TGI is notably higher than in tier-one markets.
*   **Interest Preferences:** Users prefer practical knowledge tutorials, serialized short dramas, and game livestreaming; 80% watch short dramas weekly, with average daily viewing time growing 17.2% year over year.

**Content Style Requirements:**
1.  **Practical Knowledge Layout:** Vocational skills, agricultural techniques, legal explainers, and other utility-driven content have strong market demand.
2.  **Trust Comes First:** Building a credible creator persona matters more than polished production alone; use direct, familiar communication.
3.  **Community Interaction:** Encourage repeated interactions, community identity, active fan groups, and repeat purchases.
4.  **Serialized Stickiness:** Short dramas should emphasize frequent updates and serialized continuity.
5.  **Narrative Depth:** Longer videos and story-based structures can strengthen user attachment.

**Content Keywords:** trusted creator, practical tutorials, serialized short drama, trust commerce, skill sharing, private-domain repeat purchase.
"""

PERSONA_XHS_EN = """
### Xiaohongshu Audience Profile and Content Style:

**Audience Segments:**
*   **Overall Reach:** 350M monthly active users; the platform has become a national lifestyle decision and search engine.
*   **Gender Distribution:** Male 30% / female 70%; male user growth is significant, especially in technology and outdoor categories.
*   **Age and City Distribution:** 18-35-year-old users are the core group; tier-one and new-tier-one city users account for around 60%, forming a high-value traffic pool.
*   **Interest Preferences:** 70% of monthly active users search on the platform, 88% of searches are active intent, and 90% of consumption decisions are influenced by search; high-growth areas include travel, education, and 3C home appliances.

**Content Style Requirements:**
1.  **SEO First:** Content should move from display to problem-solving; keyword match quality can decide traffic outcomes.
2.  **Value-Led Content:** Provide clear reasons to buy, pitfall-avoidance guides, or product comparisons.
3.  **Real Experience Sharing:** First-hand testing, concrete details, and honest feelings are more persuasive.
4.  **Structured Content:** Use tags, clear sections, and searchable wording; the first image strongly affects click-through.
5.  **Emotional Resonance:** Address psychological needs such as relief from work pressure and a relaxed lifestyle.

**Content Keywords:** authentic review, step-by-step guide, emotional vlog, relaxed lifestyle, active search, brand seeding.
"""

PERSONA_WX_EN = """
### WeChat Channels Audience Profile and Content Style:

**Audience Segments:**
*   **Overall Reach:** Built on WeChat's 1.4B-user ecosystem, with 1B+ monthly active users and 800M+ daily active users.
*   **Age Distribution:** Professionals aged 26-30 account for 43.7% and form the core audience; silver-haired users create a second major peak.
*   **Social Distribution Signals:** Users act as nodes in a social graph; content can spread through Moments, group chats, and private networks with naturally high trust.
*   **Interest Preferences:** Workplace insights, major brand events, private-domain exclusive content, positive stories, informative explainers, depth, and practical value.

**Content Style Requirements:**
1.  **Algorithmic Recommendation:** Recommended traffic already accounts for 54.5% and is expected to exceed 60%; content should primarily make users want to watch.
2.  **Information Density and Depth:** Emphasize viewpoints, insight, or practical interpretation.
3.  **Completion Rate Weight:** Reduce reliance on friend-like cold starts and optimize completion rate plus dwell time.
4.  **Shareability:** Give users a clear reason to share; private-domain traffic and livestream tipping are key monetization paths.
5.  **Ecosystem Support:** Connect with WeChat official accounts, mini programs, and private communities to improve the overall journey.

**Content Keywords:** career growth, private-domain loop, high-ticket conversion, brand self-broadcasting, social sharing, trust conversion.
"""

PERSONA_BILIBILI_EN = """
### Bilibili Audience Profile and Content Style:

**Audience Segments:**
*   **Overall Reach:** 348M monthly active users, with 200M users watching technology videos.
*   **Age Distribution:** Average age is around 24; the platform is less a student-only site and more a young professional community.
*   **Gender and Preferences:** Male 57% / female 43%; AI-related submissions exceed 1M, with post-2000 users accounting for around 60%; technology explainers have grown strongly.
*   **Behavior Signals:** High interaction through bullet comments, deep content consumption habits, and strong community belonging make it a key battleground for technology brands.

**Content Style Requirements:**
1.  **Mid-to-Long Video Advantage:** Lean into video essay value; watch time carries much more weight than clicks alone.
2.  **Bullet-Comment Interaction:** Design moments that invite comments, memes, and participation.
3.  **Hardcore Technology Content:** AI applications, deep science communication, and rigorous reviews are strong traffic drivers.
4.  **Information Gain:** Avoid shallow entertainment; emphasize depth and new information.
5.  **High-Ticket Conversion:** Reviews of cars, consumer electronics, and home appliances can have strong purchase influence.

**Content Keywords:** hardcore technology, deep explainer, AI application, like-coin-favorite, high-energy moment, content commerce.
"""

PLATFORM_PERSONAS_EN = {
    "douyin": PERSONA_DOUYIN_EN,
    "ks": PERSONA_KS_EN,
    "xhs": PERSONA_XHS_EN,
    "wx": PERSONA_WX_EN,
    "bilibili": PERSONA_BILIBILI_EN
}
