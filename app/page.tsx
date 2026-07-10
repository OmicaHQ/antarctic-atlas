const modules = [
  { title: "Research Universe", text: "Trace the concepts, evidence, and relationships shaping Antarctic Ice Sheet science.", image: "/research-universe.png" },
  { title: "Antarctic System", text: "Compare glaciers, ice shelves, and observation layers across a changing continent.", image: "/antarctic-system.png" },
  { title: "Mini Research Lab", text: "Explore interactive experiments and test how Antarctic systems respond.", image: "/research-lab.png" },
];

export default function Home() {
  return (
    <main>
      <nav className="nav">
        <a className="brand" href="#top" aria-label="Antarctic Atlas home"><span className="mark">A</span> Antarctic Atlas</a>
        <div className="navLinks"><a href="#explore">Explore</a><a href="#about">About</a><a className="navCta" href="https://antarctic-research-atlas.streamlit.app/">Launch atlas</a></div>
      </nav>

      <section className="hero" id="top">
        <div className="aurora auroraOne" /><div className="aurora auroraTwo" />
        <div className="eyebrow">AN INTERACTIVE RESEARCH LANDSCAPE</div>
        <h1>See Antarctica<br /><em>as a living system.</em></h1>
        <p className="lead">A visual, AI-assisted atlas for exploring the past, present, and possible futures of the Antarctic Ice Sheet.</p>
        <div className="actions">
          <a className="primary" href="https://antarctic-research-atlas.streamlit.app/">Enter the atlas <span>↗</span></a>
          <a className="secondary" href="#explore">Discover the project <span>↓</span></a>
        </div>
        <div className="heroStats"><div><strong>89</strong><span>pages of research synthesized</span></div><div><strong>6</strong><span>interactive exploration modes</span></div><div><strong>2020→</strong><span>past, present &amp; future</span></div></div>
        <div className="iceLine" aria-hidden="true" />
      </section>

      <section className="explore" id="explore">
        <div className="sectionIntro"><span>01 / EXPLORE</span><h2>Research, made visible.</h2><p>Move from evidence to insight through interconnected views of Antarctic science.</p></div>
        <div className="cards">
          {modules.map((module, index) => <article className="card" key={module.title}><img src={module.image} alt="" /><div className="cardShade" /><div className="cardCopy"><span>0{index + 1}</span><h3>{module.title}</h3><p>{module.text}</p></div></article>)}
        </div>
      </section>

      <section className="about" id="about">
        <div><span className="kicker">02 / THE SOURCE</span><h2>One landmark review.<br />A universe of questions.</h2></div>
        <div className="aboutCopy"><p>Antarctic Atlas transforms Noble et al.’s landmark review of ice-sheet sensitivity into an approachable research environment—connecting deep-time evidence, contemporary observations, and future uncertainty.</p><a href="https://github.com/OmicaHQ/antarctic-atlas">View the open-source project <span>↗</span></a></div>
      </section>

      <footer><div className="brand"><span className="mark">A</span> Antarctic Atlas</div><p>Developed by Omica Chow · Open source under MIT</p><a href="#top">Back to top ↑</a></footer>
    </main>
  );
}
