let selectedChar = 'ogami';

// キャラクター選択の制御
document.querySelectorAll('.char-option').forEach(option => {
    option.addEventListener('click', () => {
        // UI更新
        document.querySelectorAll('.char-option').forEach(opt => opt.classList.remove('active'));
        option.classList.add('active');
        
        selectedChar = option.dataset.char;
        
        // メインアバターとテキストの更新
        const avatar = document.getElementById('ogami-avatar');
        const title = document.querySelector('.title-area h1');
        const desc = document.querySelector('.title-area p');
        
        if (selectedChar === 'mio') {
            avatar.src = '/static/mio.png';
            avatar.alt = 'ミオ';
            title.textContent = 'ミオの癒やしとお導き';
            desc.textContent = 'お姉さんのように、時にはお母さんのように見守るよ';
        } else {
            avatar.src = '/static/ogami_sama.png';
            avatar.alt = '大神様';
            title.textContent = '大神様の愛の鞭';
            desc.textContent = '山の神の使い、白狼が貴様の甘えを断つ';
        }
    });
});

// ユーザー情報を取得して反映
async function fetchUserStats() {
    const userIdInput = document.getElementById('user_id');
    const userId = userIdInput.value;
    if (!userId) return;

    // ユーザーIDを保存
    localStorage.setItem('learning_support_user_id', userId);

    try {
        const response = await fetch(`/user/${encodeURIComponent(userId)}/stats`);
        if (response.ok) {
            const stats = await response.json();
            document.getElementById('consecutive_days').value = stats.consecutive_days;
        }
    } catch (error) {
        console.error("Failed to fetch user stats:", error);
    }
}

// ユーザーID入力時に情報を取得
document.getElementById('user_id').addEventListener('change', fetchUserStats);

// 初期表示時にも取得
window.addEventListener('load', () => {
    const savedUserId = localStorage.getItem('learning_support_user_id');
    if (savedUserId) {
        document.getElementById('user_id').value = savedUserId;
    }
    fetchUserStats();
});

document.getElementById('btn-generate').addEventListener('click', async () => {
    const userId = document.getElementById('user_id').value;
    const consecutiveDays = parseInt(document.getElementById('consecutive_days').value) || 0;
    const followedPlan = document.querySelector('input[name="previous_task"]:checked').value === 'true';
    const userMessage = document.getElementById('user_message').value;

    if (!userMessage.trim()) {
        alert("大神様（またはミオ）に何か言葉を捧げよ。");
        return;
    }

    // UI制御
    const btn = document.getElementById('btn-generate');
    const loader = document.getElementById('loader');
    const resultArea = document.getElementById('result-area');
    const ogamiAvatar = document.getElementById('ogami-avatar');

    btn.style.display = 'none';
    loader.style.display = 'block';
    resultArea.style.display = 'none';

    try {
        const response = await fetch('/omikuji', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: userId,
                character_id: selectedChar,
                consecutive_days: consecutiveDays,
                followed_plan: followedPlan,
                user_message: userMessage
            })
        });

        if (!response.ok) {
            throw new Error('御神託を得られなかったようだ（サーバーエラー）。');
        }

        const data = await response.json();

        // 結果の反映
        document.getElementById('fortune-badge').textContent = data.fortune;
        document.getElementById('katsu-text').textContent = data.katsu;
        document.getElementById('advice-text').textContent = data.advice;
        document.getElementById('training-text').textContent = data.next_action_advice;

        // 成功したら連続日数を再取得（自動インクリメントされた可能性を考慮）
        fetchUserStats();

        // 表示の切り替え
        loader.style.display = 'none';
        resultArea.style.display = 'block';
        
        // アニメーション効果
        ogamiAvatar.style.transform = 'scale(1.2) rotate(-5deg)';
        setTimeout(() => {
            ogamiAvatar.style.transform = 'scale(1) rotate(0deg)';
        }, 500);

        // 結果までスクロール
        resultArea.scrollIntoView({ behavior: 'smooth' });

    } catch (error) {
        alert(error.message);
        btn.style.display = 'block';
        loader.style.display = 'none';
    }
});
