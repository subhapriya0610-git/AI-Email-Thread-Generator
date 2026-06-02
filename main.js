document.addEventListener('DOMContentLoaded', () => {
    
    // Auto-hide flash messages
    const flashMessages = document.querySelectorAll('.alert');
    if (flashMessages.length > 0) {
        setTimeout(() => {
            flashMessages.forEach(msg => {
                msg.style.opacity = '0';
                setTimeout(() => msg.remove(), 400);
            });
        }, 4000);
    }

    // Generator Tabs
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            
            // Remove active class from all
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.style.display = 'none');
            
            // Add active class to clicked
            btn.classList.add('active');
            const targetId = btn.getAttribute('data-target');
            document.getElementById(targetId).style.display = 'block';
        });
    });

    // Form Submission (Generator)
    const generatorForm = document.getElementById('generatorForm');
    if (generatorForm) {
        generatorForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const btn = document.getElementById('generateBtn');
            const btnText = btn.querySelector('.btn-text');
            const loader = btn.querySelector('.loader');
            
            // Loading state
            btn.disabled = true;
            btnText.style.display = 'none';
            loader.style.display = 'inline-block';
            
            // Prepare Data
            const isThread = document.querySelector('.tab-btn.active').getAttribute('data-target') === 'thread-email';
            
            const payload = {
                type: document.getElementById('emailType').value,
                subject: document.getElementById('subject').value,
                purpose: document.getElementById('purpose').value,
                is_thread: isThread,
                thread_type: document.getElementById('threadType').value
            };
            
            try {
                const response = await fetch('/api/generate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Update UI with result
                    document.getElementById('emptyResult').style.display = 'none';
                    document.getElementById('activeResult').style.display = 'flex';
                    
                    document.getElementById('resultSubject').textContent = data.subject;
                    document.getElementById('resultContent').textContent = data.content;
                    
                    document.getElementById('copyBtn').disabled = false;
                }
            } catch (error) {
                console.error("Error generating email:", error);
                alert("Failed to generate email. Please try again.");
            } finally {
                // Restore button state
                btn.disabled = false;
                btnText.style.display = 'inline-block';
                loader.style.display = 'none';
            }
        });
    }

    // Copy functionality (Generator)
    const copyBtn = document.getElementById('copyBtn');
    if (copyBtn) {
        copyBtn.addEventListener('click', () => {
            const subject = document.getElementById('resultSubject').textContent;
            const content = document.getElementById('resultContent').textContent;
            
            const textToCopy = `Subject: ${subject}\n\n${content}`;
            
            navigator.clipboard.writeText(textToCopy).then(() => {
                const originalHtml = copyBtn.innerHTML;
                copyBtn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
                copyBtn.classList.add('btn-success');
                
                setTimeout(() => {
                    copyBtn.innerHTML = originalHtml;
                    copyBtn.classList.remove('btn-success');
                }, 2000);
            });
        });
    }

    // Dashboard History Copy
    const copyHistoryBtns = document.querySelectorAll('.copy-history-btn');
    copyHistoryBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const content = btn.getAttribute('data-content');
            navigator.clipboard.writeText(content).then(() => {
                const originalHtml = btn.innerHTML;
                btn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
                
                setTimeout(() => {
                    btn.innerHTML = originalHtml;
                }, 2000);
            });
        });
    });

    // Dashboard History View Modal
    const modal = document.getElementById('viewModal');
    if (modal) {
        const viewBtns = document.querySelectorAll('.view-history-btn');
        const closeBtn = document.querySelector('.close-modal');
        const modalSubject = document.getElementById('modalSubject');
        const modalContent = document.getElementById('modalContent');
        
        viewBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                modalSubject.textContent = btn.getAttribute('data-subject');
                modalContent.textContent = btn.getAttribute('data-content');
                modal.style.display = 'flex';
            });
        });
        
        closeBtn.addEventListener('click', () => {
            modal.style.display = 'none';
        });
        
        window.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    }
});
