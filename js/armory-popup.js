// Armory popup functionality
document.addEventListener("DOMContentLoaded", function() {
    // Character hover triggers
    const hoverTriggers = document.querySelectorAll('.hover-trigger');
    
    hoverTriggers.forEach(function(trigger) {
        const characterName = trigger.getAttribute('data-character-name');
        
        if (characterName) {
            trigger.addEventListener('mouseenter', function() {
                // Find the associated popup
                const popup = trigger.parentElement.nextElementSibling?.querySelector('.popup');
                
                if (popup) {
                    // Show popup with character info
                    popup.innerHTML = `<p>Loading character data for ${characterName}...</p>`;
                    popup.classList.remove('hidden');
                    popup.style.display = 'block';
                }
            });
            
            trigger.addEventListener('mouseleave', function() {
                // Hide popup
                const popup = trigger.parentElement.nextElementSibling?.querySelector('.popup');
                
                if (popup) {
                    popup.classList.add('hidden');
                    popup.style.display = 'none';
                }
            });
        }
    });
});