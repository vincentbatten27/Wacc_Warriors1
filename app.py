"""The WACC card.

Run from the repo root:   streamlit run app.py

Owner: the product manager. This works today on the FAKE numbers, so you can build
the page before the real numbers exist. When the developer's pull request is merged,
outputs/wacc.csv appears and the app switches to it automatically.
"""
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title='WACC card', layout='centered')

real = Path('outputs/wacc.csv')
table = pd.read_csv(real if real.exists() else 'outputs/wacc_FAKE.csv')
card = table.iloc[0]  # the client; any extra rows are peers
inputs = pd.read_csv('inputs/assumptions.csv', index_col='item')

# Checks for things that would silently break the answer.
assert abs(card['w_e'] + card['w_d'] - 1) < 1e-6, 'w_e and w_d must sum to 1'
assert 0 < card['wacc'] < 0.25, 'WACC outside 0-25%: check outputs/wacc.csv'
assert abs(card['cost_of_equity'] - (card['rf'] + card['beta'] * card['mrp'])) < 1e-6, \
    'cost_of_equity does not equal rf + beta * mrp'

if not real.exists():
    st.warning('Showing FAKE numbers. Run `python code/wacc.py` to make outputs/wacc.csv.')

st.title(f"WACC card: {card['ticker']}")
st.caption(f"Returns through {card['asof']}")

# The one sentence a CFO reads.
st.markdown(
    f"**Bottom line:** a new project with the same risk as {card['ticker']}'s existing business "
    f"should clear a hurdle rate of about **{card['wacc']:.1%}**. Projects expected to earn less "
    f"destroy value; projects riskier than the core business need a higher hurdle."
)

c1, c2, c3 = st.columns(3)
c1.metric('WACC', f"{card['wacc']:.2%}")
c2.metric('Cost of equity', f"{card['cost_of_equity']:.2%}")
c3.metric('Beta', f"{card['beta']:.2f}")

st.subheader('How the WACC is built')
after_tax_rd = card['rd'] * (1 - card['tax'])
st.markdown(
    f"- **Cost of equity** = rf + beta × mrp = {card['rf']:.2%} + {card['beta']:.2f} × {card['mrp']:.2%} "
    f"= **{card['cost_of_equity']:.2%}**\n"
    f"- **After-tax cost of debt** = rd × (1 − tax) = {card['rd']:.2%} × (1 − {card['tax']:.0%}) "
    f"= **{after_tax_rd:.2%}**\n"
    f"- **WACC** = w_e × cost of equity + w_d × after-tax cost of debt = "
    f"{card['w_e']:.0%} × {card['cost_of_equity']:.2%} + {card['w_d']:.0%} × {after_tax_rd:.2%} "
    f"= **{card['wacc']:.2%}**"
)

st.subheader('Inputs and sources')
shown = inputs.copy()
shown['value'] = shown['value'].map(lambda v: f'{v:.2%}')
st.dataframe(shown, width='stretch')
missing = shown.index[shown['source'].str.startswith('TODO')].tolist()
if missing:
    st.warning(f"Sources still to be filled in by the analyst: {', '.join(missing)}")

st.subheader('What if?')
st.caption(
    'Move the sliders to see how the WACC responds. As debt changes, beta is re-levered '
    '(Hamada) because more debt makes equity riskier. The cost of debt is held fixed.'
)
w_d = st.slider('Debt weight (w_d)', 0.0, 80.0, float(card['w_d'] * 100), 1.0, format='%.0f%%') / 100
mrp = st.slider('Market risk premium', 3.0, 8.0, float(card['mrp'] * 100), 0.25, format='%.2f%%') / 100

beta_u = card['beta'] / (1 + (1 - card['tax']) * card['w_d'] / card['w_e'])
beta_new = beta_u * (1 + (1 - card['tax']) * w_d / (1 - w_d))
coe_new = card['rf'] + beta_new * mrp
wacc_new = (1 - w_d) * coe_new + w_d * after_tax_rd

d1, d2, d3 = st.columns(3)
d1.metric('WACC', f'{wacc_new:.2%}', f"{(wacc_new - card['wacc']) * 100:+.2f} pp", delta_color='inverse')
d2.metric('Cost of equity', f'{coe_new:.2%}', f"{(coe_new - card['cost_of_equity']) * 100:+.2f} pp",
          delta_color='inverse')
d3.metric('Beta (re-levered)', f'{beta_new:.2f}', f"{beta_new - card['beta']:+.2f}", delta_color='inverse')

st.subheader('Compared with peers')
if len(table) > 1:
    peers = table[['ticker', 'beta', 'cost_of_equity', 'w_d', 'wacc']].set_index('ticker')
    st.dataframe(
        peers.style.format({'beta': '{:.2f}', 'cost_of_equity': '{:.2%}', 'w_d': '{:.0%}', 'wacc': '{:.2%}'}),
        width='stretch',
    )
else:
    st.caption('No peers yet. Ask the developer to add one or two competitor rows to outputs/wacc.csv.')
