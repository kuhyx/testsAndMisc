# Texas Hold'em Modifier App

A fun web application that randomly applies modifiers to Texas Hold'em poker games with configurable probability.

## Features

- **Configurable Probability**: Adjust the chance of getting a modifier (0-100%)
- **15 Unique Modifiers**: Various game-changing rules like "High Stakes", "Wild Card", "Reverse Psychology", etc.
- **Statistics Tracking**: Keep track of rounds played and modifiers applied
- **Beautiful UI**: Modern, responsive design with poker-themed styling
- **Smooth Animations**: Visual feedback for button clicks and result displays

## How to Use

1. Open `index.html` in your web browser
2. Adjust the "Modifier Probability" slider to set the chance of getting a modifier
3. Click "Start Round" to begin a new round
4. The app will randomly decide whether to apply a modifier based on your probability setting
5. If a modifier is chosen, a random modifier will be selected and displayed

## Modifiers Included

- **High Stakes**: All bets are doubled
- **Wild Card**: Next card can be used as any card
- **Bluff Master**: See one opponent's card before betting
- **All-In Fever**: If someone goes all-in, everyone must match or fold
- **Lucky Sevens**: Any hand with a 7 beats a pair
- **Reverse Psychology**: Lowest hand wins
- **Split Pot**: Pot split between top 2 hands
- **Texas Twister**: Each player gets an extra hole card
- **Blind Luck**: Play blind until the river
- **Community Boost**: Extra community card revealed
- **Minimum Madness**: Minimum bet tripled
- **Suit Supremacy**: Random suit cards worth +1 rank
- **Quick Draw**: Betting time cut in half
- **Royal Treatment**: Face cards worth double
- **Chip Challenge**: Winner gets extra house chips

## Files

- `index.html`: Main HTML structure
- `style.css`: Styling and responsive design
- `script.js`: JavaScript functionality and modifier logic

## Customization

You can easily add new modifiers by using the `addModifier()` method:

```javascript
window.pokerApp.addModifier(
  "Your Modifier Name",
  "Description of what it does",
);
```

## Browser Compatibility

Works in all modern web browsers (Chrome, Firefox, Safari, Edge).
