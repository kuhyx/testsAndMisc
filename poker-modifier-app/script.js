class PokerModifierApp {
    constructor() {
        this.modifiers = [
            {
                name: "High Stakes",
                description: "All bets are doubled this round!"
            },
            {
                name: "Wild Card",
                description: "The next card revealed can be used as any card!"
            },
            {
                name: "Bluff Master",
                description: "Players can see one opponent's card before betting."
            },
            {
                name: "All-In Fever",
                description: "If someone goes all-in, everyone must match or fold."
            },
            {
                name: "Lucky Sevens",
                description: "Any hand with a 7 beats a pair!"
            },
            {
                name: "Reverse Psychology",
                description: "Lowest hand wins this round!"
            },
            {
                name: "Split Pot",
                description: "The pot is split between the top 2 hands."
            },
            {
                name: "Texas Twister",
                description: "Each player gets an extra hole card this round."
            },
            {
                name: "Blind Luck",
                description: "All players must play blind (no looking at cards) until the river."
            },
            {
                name: "Community Boost",
                description: "An extra community card is revealed (6 total)."
            },
            {
                name: "Minimum Madness",
                description: "Minimum bet is tripled this round."
            },
            {
                name: "Suit Supremacy",
                description: "All cards of the chosen suit (random) are worth +1 rank."
            },
            {
                name: "Quick Draw",
                description: "Betting time is cut in half - make decisions fast!"
            },
            {
                name: "Royal Treatment",
                description: "Face cards (J, Q, K) are worth double."
            },
            {
                name: "Chip Challenge",
                description: "Winner gets extra chips from the house!"
            }
        ];
        
        this.roundsPlayed = 0;
        this.modifiersApplied = 0;
        
        this.initializeElements();
        this.attachEventListeners();
        this.updateChanceDisplay();
    }
    
    initializeElements() {
        this.startButton = document.getElementById('startRoundBtn');
        this.resultDisplay = document.getElementById('resultDisplay');
        this.modifierChanceSlider = document.getElementById('modifierChance');
        this.chanceValueDisplay = document.getElementById('chanceValue');
        this.roundsCountDisplay = document.getElementById('roundsCount');
        this.modifiersCountDisplay = document.getElementById('modifiersCount');
    }
    
    attachEventListeners() {
        this.startButton.addEventListener('click', () => this.startRound());
        this.modifierChanceSlider.addEventListener('input', () => this.updateChanceDisplay());
    }
    
    updateChanceDisplay() {
        const chance = this.modifierChanceSlider.value;
        this.chanceValueDisplay.textContent = `${chance}%`;
    }
    
    startRound() {
        // Add button animation
        this.startButton.style.transform = 'scale(0.95)';
        setTimeout(() => {
            this.startButton.style.transform = '';
        }, 150);
        
        // Update round counter
        this.roundsPlayed++;
        this.roundsCountDisplay.textContent = this.roundsPlayed;
        
        // Get current probability
        const modifierChance = parseInt(this.modifierChanceSlider.value);
        
        // Determine if a modifier should be applied
        const randomValue = Math.random() * 100;
        const shouldApplyModifier = randomValue < modifierChance;
        
        if (shouldApplyModifier) {
            this.applyRandomModifier();
        } else {
            this.showNoModifier();
        }
        
        // Add some visual feedback with animation
        this.resultDisplay.style.opacity = '0';
        this.resultDisplay.style.transform = 'scale(0.8)';
        
        setTimeout(() => {
            this.resultDisplay.style.opacity = '1';
            this.resultDisplay.style.transform = 'scale(1)';
        }, 200);
    }
    
    applyRandomModifier() {
        // Update modifier counter
        this.modifiersApplied++;
        this.modifiersCountDisplay.textContent = this.modifiersApplied;
        
        // Select random modifier
        const randomIndex = Math.floor(Math.random() * this.modifiers.length);
        const selectedModifier = this.modifiers[randomIndex];
        
        // Update display
        this.resultDisplay.className = 'result-display has-modifier';
        this.resultDisplay.innerHTML = `
            <div class="modifier-title">🎲 ${selectedModifier.name}</div>
            <div class="modifier-description">${selectedModifier.description}</div>
        `;
    }
    
    showNoModifier() {
        this.resultDisplay.className = 'result-display no-modifier';
        this.resultDisplay.innerHTML = `
            <div class="no-modifier-text">No modifier this round</div>
            <div style="font-size: 0.9rem; color: #999; margin-top: 0.5rem;">Play normally</div>
        `;
    }
    
    // Method to add new modifiers (for future expansion)
    addModifier(name, description) {
        this.modifiers.push({ name, description });
    }
    
    // Method to get statistics
    getStats() {
        return {
            roundsPlayed: this.roundsPlayed,
            modifiersApplied: this.modifiersApplied,
            modifierRate: this.roundsPlayed > 0 ? (this.modifiersApplied / this.roundsPlayed * 100).toFixed(1) : 0
        };
    }
}

// Initialize the app when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.pokerApp = new PokerModifierApp();
    
    // Add some console info for developers
    console.log('🃏 Texas Hold\'em Modifier App loaded!');
    console.log('Access the app instance via window.pokerApp');
    console.log('Available methods: getStats(), addModifier(name, description)');
});
